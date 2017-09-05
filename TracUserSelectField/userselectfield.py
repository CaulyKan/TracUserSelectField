# -*- coding: utf8 -*-

from trac.core import *
from trac.ticket import TicketSystem, TicketFieldList
from trac.cache import cached
from trac.perm import PermissionSystem, PermissionCache
from trac.web import IRequestHandler
from trac.ticket.default_workflow import ConfigurableTicketWorkflow


class UserSelectFieldPlugin(Component):

    implements(IRequestHandler)

    def __init__(self):
        ts = TicketSystem(self.env)
        ts.__class__ = UserSelectFieldPlugin.PatchedTicketSystem

        ctw = ConfigurableTicketWorkflow(self.env)
        ctw._to_users = self.patched_to_users

    def match_request(self, req):
        return False

    def process_request(self, req):
        pass

    def patched_to_users(self, users_perms_and_groups, ticket):
        """Finds all users contained in the list of `users_perms_and_groups`
        by recursive lookup of users when a `group` is encountered.
        """
        ps = PermissionSystem(self.env)
        groups = ps.get_groups_dict()

        def append_owners(users_perms_and_groups):
            for user_perm_or_group in users_perms_and_groups:
                if user_perm_or_group == 'authenticated':
                    owners.update(set(u[0] for u in self.env.get_known_users()))
                elif user_perm_or_group.isupper():
                    perm = user_perm_or_group
                    for user in ps.get_users_with_permission(perm):
                        if perm in PermissionCache(self.env, user,
                                                   ticket.resource):
                            owners.add(user)
                elif user_perm_or_group.startswith('$'):
                    if ticket[user_perm_or_group[1:]] != None:
                        owners.add(ticket[user_perm_or_group[1:]])
                elif user_perm_or_group not in groups:
                    owners.add(user_perm_or_group)
                else:
                    append_owners(groups[user_perm_or_group])

        owners = set()
        append_owners(users_perms_and_groups)

        return sorted(owners)

    class PatchedTicketSystem(TicketSystem):

        @cached
        def custom_fields(self):
            """Return the list of custom ticket fields available for tickets."""
            fields = TicketFieldList()
            config = self.ticket_custom_section
            for name in [option for option, value in config.options()
                         if '.' not in option]:
                field = {
                    'name': name,
                    'custom': True,
                    'type': config.get(name),
                    'order': config.getint(name + '.order', 0),
                    'label': config.get(name + '.label') or
                             name.replace("_", " ").strip().capitalize(),
                    'value': config.get(name + '.value', '')
                }
                if field['type'] == 'select' or field['type'] == 'radio':
                    if config.get(name + '.format', None) == 'user':
                        userStr = config.get(name + '.user', 'authenticated').split(',')
                        users = self._to_users(userStr)
                        field['options'] = users
                    else:
                        field['options'] = config.getlist(name + '.options', sep='|')
                        if '' in field['options'] or \
                                field['name'] in self.allowed_empty_fields:
                            field['optional'] = True
                            if '' in field['options']:
                                field['options'].remove('')
                elif field['type'] == 'text':
                    field['format'] = config.get(name + '.format', 'plain')
                elif field['type'] == 'textarea':
                    field['format'] = config.get(name + '.format', 'plain')
                    field['height'] = config.getint(name + '.rows')
                elif field['type'] == 'time':
                    field['format'] = config.get(name + '.format', 'datetime')
                fields.append(field)

            fields.sort(lambda x, y: cmp((x['order'], x['name']),
                                         (y['order'], y['name'])))
            return fields

        def _to_users(self, users_perms_and_groups):
            """Finds all users contained in the list of `users_perms_and_groups`
            by recursive lookup of users when a `group` is encountered.
            """
            ps = PermissionSystem(self.env)
            groups = ps.get_groups_dict()

            def append_owners(users_perms_and_groups):
                for user_perm_or_group in users_perms_and_groups:
                    if user_perm_or_group == 'authenticated':
                        owners.update(set(u[0] for u in self.env.get_known_users()))
                    elif user_perm_or_group.isupper():
                        perm = user_perm_or_group
                        for user in ps.get_users_with_permission(perm):
                            owners.add(user)
                    elif user_perm_or_group not in groups:
                        owners.add(user_perm_or_group)
                    else:
                        append_owners(groups[user_perm_or_group])

            owners = set()
            append_owners(users_perms_and_groups)

            return sorted(owners)
