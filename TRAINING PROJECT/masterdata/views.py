from django.http import JsonResponse
from .models import State, District

def get_states(request):
    country_id = request.GET.get('country_id')
    if country_id:
        states = State.objects.filter(country_id=country_id, is_active=True).values('id', 'name').order_by('display_order', 'name')
        return JsonResponse(list(states), safe=False)
    return JsonResponse([], safe=False)

def get_districts(request):
    state_id = request.GET.get('state_id')
    if state_id:
        districts = District.objects.filter(state_id=state_id, is_active=True).values('id', 'name').order_by('display_order', 'name')
        return JsonResponse(list(districts), safe=False)
    return JsonResponse([], safe=False)
