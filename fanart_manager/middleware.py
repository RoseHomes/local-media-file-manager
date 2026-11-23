from ipaddress import ip_address

from django.http import HttpResponseForbidden


def local_requests_only(get_response):
    def middleware(request):
        # Use the socket peer recorded by the server, never a forwarded header.
        try:
            remote_address = ip_address(request.META.get("REMOTE_ADDR", ""))
        except ValueError:
            return HttpResponseForbidden()
        if not remote_address.is_loopback:
            return HttpResponseForbidden()
        request.get_host()
        return get_response(request)

    return middleware
