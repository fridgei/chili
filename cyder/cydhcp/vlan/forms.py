from django import forms

from cyder.cydhcp.vlan.models import Vlan


class VlanForm(forms.ModelForm):
    #site = forms.ModelChoiceField(queryset=Site.objects.all())

    class Meta:
        model = Vlan
