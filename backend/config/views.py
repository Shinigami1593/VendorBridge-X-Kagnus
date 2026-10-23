from django.http import JsonResponse


def server_error(request):
    return JsonResponse(
        {'detail': 'Internal server error.'},
        status=500,
    )
