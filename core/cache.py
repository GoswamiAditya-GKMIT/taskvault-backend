import hashlib
from django.core.cache import cache

def invalidate_tenant_cache(organization_id):

    key = f"previous_cache_version:{organization_id}"
    try:
        # Increment the version. If it doesn't exist, it starts at 1.
        cache.incr(key)
    except ValueError:
        cache.set(key, 1)

def get_tenant_cache_version(organization_id):
    """
    Retrieves the current cache generation version for a tenant.
    """
    key = f"previous_cache_version:{organization_id}"
    version = cache.get(key)
    if version is None:
        version = 1
        cache.set(key, version)
    return version

def generate_cache_key(user, view_instance, request):

    if not user.is_authenticated or not hasattr(user, 'organization'):
        return None

    organization_id = user.organization.id
    user_id = user.id
    view_name = view_instance.__class__.__name__
    
    # Sort query params to ensure consistent keys for same params in different order
    query_params = request.query_params.dict()
    sorted_params = sorted(query_params.items())
    params_string = str(sorted_params)
    params_hash = hashlib.md5(params_string.encode('utf-8')).hexdigest()

    version = get_tenant_cache_version(organization_id)

    # Key format:
    # cache:tenant:{org_id}:gen:{version}:user:{user_id}:view:{view_name}:params:{hash}
    cache_key = (
        f"cache:tenant:{organization_id}:"
        f"gen:{version}:"
        f"user:{user_id}:"
        f"view:{view_name}:"
        f"params:{params_hash}"
    )
    
    return cache_key
