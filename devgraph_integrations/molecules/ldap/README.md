# LDAP Molecule

The LDAP molecule provides integration with LDAP directories to discover and manage users, groups, and organizational units as entities in the Devgraph system.

## Overview

This molecule connects to LDAP directories (Active Directory, OpenLDAP, etc.) to discover directory objects and creates corresponding entities in the Devgraph. It supports multiple search selectors for different object types and handles pagination for large directories.

## Entities Created

- **LDAP User**: Represents user accounts from the directory
- **LDAP Group**: Represents groups/security groups
- **LDAP Organizational Unit**: Represents organizational units (OUs)

## Configuration

The LDAP provider is configured using the `LdapProviderConfig` class:

```yaml
providers:
  - name: ldap-provider
    type: ldap
    every: 600  # Run every 10 minutes
    config:
      namespace: default
      server: ldap.example.com
      port: 389
      use_tls: true
      use_ssl: false
      bind_dn: cn=readonly,dc=example,dc=com
      bind_password: ${LDAP_PASSWORD}
      timeout: 30
      page_size: 1000
      user_selectors:
        - base_dn: ou=Users,dc=example,dc=com
          search_filter: "(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
          search_scope: SUBTREE
          attributes: ["*"]
      group_selectors:
        - base_dn: ou=Groups,dc=example,dc=com
          search_filter: "(objectClass=group)"
          search_scope: SUBTREE
          attributes: ["*"]
      org_unit_selectors:
        - base_dn: dc=example,dc=com
          search_filter: "(objectClass=organizationalUnit)"
          search_scope: SUBTREE
          attributes: ["*"]
```

### Configuration Options

- `namespace`: Kubernetes-style namespace for created entities
- `server`: LDAP server hostname or IP address
- `port`: LDAP server port (389 for plain, 636 for SSL)
- `use_tls`: Whether to use STARTTLS encryption
- `use_ssl`: Whether to use SSL/TLS connection
- `bind_dn`: Distinguished name for authentication (None for anonymous)
- `bind_password`: Password for authentication
- `timeout`: Connection timeout in seconds
- `page_size`: Page size for paginated searches
- `user_selectors`: List of selectors for discovering user objects
- `group_selectors`: List of selectors for discovering group objects
- `org_unit_selectors`: List of selectors for discovering OU objects

### Selector Configuration

Each selector defines:
- `base_dn`: Base distinguished name to start search from
- `search_filter`: LDAP search filter (defaults to all objects)
- `search_scope`: Search scope (BASE, ONELEVEL, or SUBTREE)
- `attributes`: List of attributes to retrieve (["*"] for all)

## Authentication

The provider supports multiple authentication methods:

1. **Anonymous binding**: Leave `bind_dn` and `bind_password` as null
2. **Simple authentication**: Provide bind DN and password
3. **Service account**: Use a dedicated read-only service account

## Search Capabilities

- **Paginated searches**: Handles large result sets efficiently
- **Multiple scopes**: BASE, ONELEVEL, and SUBTREE searches
- **Flexible filters**: Supports complex LDAP search filters
- **Attribute selection**: Choose specific attributes or retrieve all

## Example Search Filters

### Active Directory Users (Enabled Only)
```ldap
(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))
```

### Security Groups
```ldap
(&(objectClass=group)(groupType:1.2.840.113556.1.4.803:=2147483648))
```

### Service Accounts
```ldap
(&(objectClass=user)(servicePrincipalName=*))
```

## Example Entities

### LDAP User Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: LdapUser
metadata:
  name: jdoe
  namespace: default
spec:
  dn: cn=John Doe,ou=Users,dc=example,dc=com
  attributes:
    sAMAccountName: jdoe
    displayName: John Doe
    mail: jdoe@example.com
    department: Engineering
    title: Software Engineer
```

### LDAP Group Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: LdapGroup
metadata:
  name: developers
  namespace: default
spec:
  dn: cn=Developers,ou=Groups,dc=example,dc=com
  attributes:
    cn: Developers
    description: Developer group
    member:
      - cn=John Doe,ou=Users,dc=example,dc=com
      - cn=Jane Smith,ou=Users,dc=example,dc=com
```

### LDAP Organizational Unit Entity
```yaml
apiVersion: entities.devgraph.io/v1
kind: LdapOrgUnit
metadata:
  name: engineering
  namespace: default
spec:
  dn: ou=Engineering,dc=example,dc=com
  attributes:
    ou: Engineering
    description: Engineering department
```

## Error Handling

The provider implements comprehensive error handling:

- Graceful connection failure handling
- Continues processing if individual searches fail
- Detailed logging for troubleshooting
- Connection cleanup and resource management

## Security Considerations

- Use read-only service accounts when possible
- Enable TLS/SSL for production environments
- Limit attribute access to necessary fields only
- Monitor connection logs for security events

## Files

- `config.py`: Configuration models for LDAP settings and selectors
- `client.py`: LDAP client implementation with search capabilities
- `types/`: Entity type definitions for users, groups, and OUs
- `types/relations.py`: Relationship definitions

## Dependencies

- `ldap3`: Pure Python LDAP library
- `loguru`: Logging
- `pydantic`: Configuration validation

## Troubleshooting

### Connection Issues
- Verify server hostname and port
- Check firewall rules
- Test with ldapsearch command-line tool

### Authentication Problems
- Validate bind DN format
- Ensure service account has read permissions
- Check password expiration

### Search Performance
- Optimize search filters
- Reduce page size for slower servers
- Consider indexing on frequently searched attributes