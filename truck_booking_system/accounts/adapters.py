from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import PermissionDenied


class GmailOnlyAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email")

        if not email or not email.endswith("@gmail.com"):
            raise PermissionDenied("Only Gmail accounts are allowed")
