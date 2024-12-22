from lemonsqueezy import LemonSqueezy
from django.conf import settings
from django.http import JsonResponse

def get_store_id():
    try:
        # Initialize LemonSqueezy client
        client = LemonSqueezy(api_key=settings.LEMONSQUEEZY_API_KEY)
        
        # Get list of stores
        stores = client.list_stores()
        
        # Print all stores for reference
        print("\nAvailable Stores:")
        for store in stores.get('data', []):
            print(f"Store Name: {store['attributes']['name']}")
            print(f"Store ID: {store['id']}")
            print(f"Store URL: {store['attributes']['url']}")
            print("-------------------")
        
        # Return the first store ID if exists
        if stores.get('data'):
            return stores['data'][0]['id']
        return None
        
    except Exception as e:
        print(f"Error retrieving store ID: {str(e)}")
        return None

# Usage example:
def test_get_store_id(request):
    store_id = get_store_id()
    if store_id:
        print(f"Your store ID is: {store_id}")
        return JsonResponse({
            'status': 'success',
            'store_id': store_id
        })
    return JsonResponse({
        'status': 'error',
        'message': 'Could not retrieve store ID'
    })
