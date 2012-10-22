from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
from django.contrib import messages
from django.forms.util import ErrorList, ErrorDict
from django.http import HttpResponse

from cyder.cydhcp.network.models import Network, NetworkKeyValue
from cyder.cydhcp.network.forms import *
from cyder.cydhcp.network.utils import calc_networks, calc_parent_str
from cyder.cydhcp.vlan.models import Vlan
from cyder.cydhcp.site.models import Site
from cyder.cydhcp.site.forms import SiteForm
from cyder.cydhcp.keyvalue.utils import get_attrs, update_attrs
from cyder.cydhcp.range.forms import RangeForm

from cyder.cydhcp.views import CoreDeleteView, CoreListView
from cyder.cydhcp.views import CoreCreateView
from cyder.cydns.ip.models import ipv6_to_longs
from django.forms.formsets import formset_factory

import re
import pdb
import ipaddr


def network_wizard(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == "network":
            # return the allocate network block page.
            form = NetworkForm_network(request.POST)
            try:
                ip_type = form.data.get('ip_type')
                if ip_type not in ('4', '6'):
                    raise ValidationError("IP type must be either IPv4 or "
                                          "IPv6.")
                network_str = form.data.get('network', '')
                try:
                    if ip_type == '4':
                        network = ipaddr.IPv4Network(network_str)
                    elif ip_type == '6':
                        network = ipaddr.IPv6Network(network_str)
                except ipaddr.AddressValueError, e:
                    raise ValidationError("Bad Ip address {0}".format(e))
                except ipaddr.NetmaskValueError, e:
                    raise ValidationError("Bad Netmask {0}".format(e))

                # Make sure this network doesn't exist.
                if ip_type == '4':
                    ip_upper, ip_lower = 0, int(network.network)
                else:
                    ip_upper, ip_lower = ipv6_to_longs(network.network)
                if (Network.objects.filter(ip_upper=ip_upper,
                                           ip_lower=ip_lower).exists()):
                    raise ValidationError("This network has already been "
                                          "allocated.")
            except ValidationError, e:
                form = NetworkForm_network(request.POST)
                if form._errors is None:
                    form._errors = ErrorDict()
                form._errors['__all__'] = ErrorList(e.messages)
                return render(request, 'network/wizard_form.html', {
                    'form': form,
                    'action': 'network'
                })

            request.session['net_wiz_vars'] = {'ip_type': ip_type,
                                               'network_str': str(network)}
            parent = calc_parent_str(network_str, ip_type=ip_type)

            # Now build the form with the correct site.
            form = NetworkForm_site()
            if parent:
                form.fields['site'].initial = parent.site
            else:
                form = NetworkForm_site()

            return render(request, 'network/wizard_form.html', {
                'form': form,
                'action': 'site'
            })
        elif action == "site":
            # We are looking for the user to choose a site.
            form = NetworkForm_site(request.POST)
            nvars = request.session['net_wiz_vars']
            try:
                form.is_valid()
                site = form.data.get('site', False)
                if not site:
                    site = None
                    nvars['site_pk'] = None
                else:
                    try:
                        site = Site.objects.get(pk=site)
                        nvars['site_pk'] = site.pk
                    except ObjectDoesNotExist, e:
                        raise ValidationError("That site does not exist. Try"
                                              " again.")
            except ValidationError, e:
                form = NetworkForm_site(request.POST)
                if form._errors is None:
                    form._errors = ErrorDict()
                form._errors['__all__'] = ErrorList(e.messages)
                return render(request, 'network/wizard_form.html', {
                    'form': form,
                    'action': 'site'
                })
            # Validation
            # return the choose or create vlan page.
            form = NetworkForm_vlan()
            # return the allocate network block page.
            return render(request, 'network/wizard_form.html', {
                'form': form,
                'action': 'vlan',
            })

        elif action == "vlan":
            form = NetworkForm_vlan(request.POST)
            try:
                form.is_valid()
                nvars = request.session['net_wiz_vars']
                if 'create_choice' not in form.data:
                    raise ValidationError("Select whether you are using an "
                                          "exiting Vlan or if you are going to make a "
                                          "new one.")
                create_choice = form.data['create_choice']
                if create_choice == 'new':
                    if 'name' not in form.data:
                        raise ValidationError("When creating a new Vlan, "
                                              "please provide a vlan name")
                    if 'number' not in form.data:
                        raise ValidationError("When creating a new Vlan, "
                                              "please provide a vlan number")
                    vlan_name = form.data['name']
                    vlan_number = form.data['number']
                    if not (vlan_name and vlan_number):
                        raise ValidationError("When creating a new Vlan, "
                                              "please provide a string for the name and "
                                              "an integer for the number.")
                    vlan = Vlan.objects.filter(name=vlan_name,
                                               number=vlan_number).exists()
                    if vlan:
                        raise ValidationError("The Vlan {0} {1} already "
                                              "exists.".format(vlan_name, vlan_number))
                    else:
                        nvars['vlan_action'] = "new"
                        nvars['vlan_name'] = vlan_name
                        nvars['vlan_number'] = vlan_number
                elif create_choice == 'existing':
                    nvars['vlan_action'] = "existing"
                    vlan = form.data.get('vlan', '')
                    if not vlan:
                        raise ValidationError("You selected to use an existing"
                                              "vlan. Pleasechoose a vlan.")
                    try:
                        vlan = Vlan.objects.get(pk=vlan)
                    except ObjectDoesNotExist, e:
                        raise ValidationError("That Vlan does not exist. Try "
                                              "again.")
                    nvars['vlan_pk'] = vlan.pk
                    nvars['vlan_action'] = "existing"
                else:
                    nvars['vlan_action'] = "none"

                site, network, vlan = create_objects(nvars)
            except ValidationError, e:
                form = NetworkForm_vlan(request.POST)
                if form._errors is None:
                    form._errors = ErrorDict()
                form._errors['__all__'] = ErrorList(e.messages)
                return render(request, 'network/wizard_form.html', {
                    'form': form,
                    'action': 'vlan'
                })

            return render(request, 'network/wizard_range.html', {
                'network': network,
                'vlan': vlan,
                'action': 'confirm',
            })
            """
            # Soon.
            RangeFormSet = formset_factory(RangeForm, extra=4)
            request.session['net_wiz_vars'] = nvars
            network.update_network()
            #range_formset = RangeFormSet(initial = {
            #    'start_str':str(network.network.network),
            #    'end_str':str(network.network.broadcast)
            #})
            range_formset = RangeFormSet(initial=[
                {'network':network,
                'start_str': str(network.network.network),
                'end_str': str(ipaddr.IPv4Address(int(network.network.broadcast
                                - 1)))
                }])
            return render(request, 'network/wizard_range.html', {
                'network': network,
                'vlan': vlan,
                'site': vlan,
                'action': 'ranges',
                'range_formset': range_formset,
            })

        elif action == "ranges":
            nvars = request.session['net_wiz_vars']
            pass
            """
        elif action == "confirm":
            nvars = request.session['net_wiz_vars']
            site, network, vlan = create_objects(nvars)
            if site:
                site.save()
            if vlan:
                vlan.save()
                network.vlan = vlan
            network.save()
            del request.session['net_wiz_vars']
            return redirect(network)

    # Catch everything else.
    # return the allocate network block page.
    form = NetworkForm_network()
    # return the allocate network block page.
    return render(request, 'network/wizard_form.html', {
        'form': form,
        'action': 'network',
    })


def create_objects(nvars):
    # There needs to be major exception handling here. Things can go pretty
    # wrong.
    ip_type = nvars.get('ip_type', None)
    network_str = nvars.get('network_str', None)
    network = Network(network_str=network_str, ip_type=ip_type)
    network.update_network()

    site_pk = nvars.get('site_pk', '')
    if not site_pk:
        site = None
    else:
        site = Site.objects.get(pk=site_pk)

    network.site = site

    if nvars.get('vlan_action', '') == "new":
        vlan_name = nvars.get('vlan_name', None)
        vlan_number = nvars.get('vlan_number', None)
        vlan = Vlan(name=vlan_name, number=vlan_number)
    elif nvars.get('vlan_action', '') == "existing":
        vlan_number = nvars.get('vlan_pk', '')
        if not vlan_number:
            raise ValidationError("You selected to use an existing vlan. "
                                  "Pleasechoose a vlan.")
        vlan = Vlan.objects.get(pk=vlan_number)
    else:
        vlan = None

    network.vlan = vlan

    return site, network, vlan