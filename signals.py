import logging

from django.dispatch import receiver
from django.shortcuts import get_object_or_404

from coldfront.core.allocation.signals import (
    allocation_activate,
    allocation_activate_user,
    allocation_remove_user,
)
from coldfront.core.allocation.models import Allocation, AllocationUser

# from coldfront.core.resource.models import *
from coldfront.plugins.ldap_allocs.utils import LDAPModify, get_group_name

logger = logging.getLogger(__name__)


@receiver(allocation_remove_user)
def alloc_remove_user(sender, **kwargs):
    allocation_user_id = kwargs.get("allocation_user_pk")
    allocation_user = get_object_or_404(AllocationUser, pk=allocation_user_id)
    # logger.debug(allocation_user.user.username)
    allocation_obj = allocation_user.allocation
    if allocation_obj.status.name != "Active":
        return
    ldap_group_name = get_group_name(allocation_obj)
    if ldap_group_name is None:
        return
    ldap_sam = LDAPModify()
    ldap_sam.remove_user_from_group(ldap_group_name, allocation_user.user.username)


@receiver(allocation_activate_user)
def alloc_activate_user(sender, **kwargs):
    allocation_user_id = kwargs.get("allocation_user_pk")
    allocation_user = get_object_or_404(AllocationUser, pk=allocation_user_id)
    # logger.debug(allocation_user.user.username)
    allocation_obj = allocation_user.allocation
    if allocation_obj.status.name != "Active":
        return

    ldap_group_name = get_group_name(allocation_obj)
    if ldap_group_name is None:
        return

    ldap_sam = LDAPModify()
    ldap_sam.add_user_to_group(ldap_group_name, allocation_user.user.username)
    # allocation_activate.send(sender=None, allocation_pk=allocation_obj.pk)


# @receiver(allocation_disable)
# def alloc_disable(sender, **kwargs):
#     allocation_id = kwargs.get("allocation_pk")
#     allocation_obj = get_object_or_404(Allocation, pk=allocation_id)
#     ldap_sam = LDAPModify()
#     for resource in allocation_obj.resources.all():
#         ldap_group_name = resource.get_attribute("ldap-group-name")
#         groups = ldap_sam.search_a_group(ldap_group_name, objectClass="groups")
#         for user in allocation_obj.project.projectuser_set.filter(
#             ~Q(status__name="Active")
#         ):
#             ldap_sam.remove_user_from_group(ldap_group_name, user.user.username)


@receiver(allocation_activate)
def alloc_activate(sender, **kwargs):
    allocation_id = kwargs.get("allocation_pk")
    allocation_obj = get_object_or_404(Allocation, pk=allocation_id)

    # each project will only be able to have one group for each allocation resource type
    ldap_group_name = get_group_name(allocation_obj)
    if ldap_group_name is None:
        return

    ldap_sam = LDAPModify()
    groups = ldap_sam.search_a_group(ldap_group_name, objectClass="groups")
    # logger.debug(f"Groups: {groups}")
    if len(groups) == 0:
        # create group
        ldap_sam.create_group(
            ldap_group_name, "posixGroup", {"gidNumber": allocation_id}
        )
    groups = ldap_sam.search_a_group(ldap_group_name, objectClass="groups")
    if len(groups) == 0:
        logger.critical(f"Failed to create group {ldap_group_name}")
        return
    # for user in allocation_obj.project.projectuser_set.filter(status__name="Active"):
    #     ldap_sam.add_user_to_group(ldap_group_name, user.user.username)
    # logger.debug(f"Groups: {groups}")
