from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse


class CORSMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware to ensure CORS headers are always present
    """
    
    def process_response(self, request, response):
        # Add CORS headers to all responses
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = JsonResponse({'message': 'CORS preflight'})
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Max-Age'] = '86400'
        
        return response
