import requests
import hashlib
import json
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from datetime import datetime

class SSLCommerzService:
    """SSLCommerz payment gateway integration service"""
    
    def __init__(self):
        # Production credentials
        self.store_id = 'ts68c1700491a82'
        self.store_password = 'ts68c1700491a82@ssl'
        self.base_url = 'https://sandbox.sslcommerz.com'
        self.success_url = 'https://react-final.vercel.app/payment-success'
        self.fail_url = 'https://react-final.vercel.app/payment-failed'
        self.cancel_url = 'https://react-final.vercel.app/payment-cancelled'
        self.ipn_url = 'https://django-final.vercel.app/api/payments/sslcommerz/ipn/'
    
    def generate_hash(self, data):
        """Generate hash for SSLCommerz authentication"""
        hash_string = f"{self.store_password}{data['tran_id']}{data['total_amount']}{data['currency']}"
        return hashlib.sha512(hash_string.encode()).hexdigest()
    
    def create_session(self, order, payment):
        """Create SSLCommerz payment session"""
        try:
            # Generate transaction ID
            tran_id = f"TXN_{order.id.hex[:8].upper()}_{int(timezone.now().timestamp())}"
            
            # Prepare payment data
            payment_data = {
                'store_id': self.store_id,
                'store_passwd': self.store_password,
                'total_amount': str(order.total_amount),
                'currency': 'BDT',
                'tran_id': tran_id,
                'success_url': self.success_url,
                'fail_url': self.fail_url,
                'cancel_url': self.cancel_url,
                'emi_option': '0',
                'cus_name': f"{order.buyer.first_name} {order.buyer.last_name}".strip() or order.buyer.email,
                'cus_email': order.buyer.email,
                'cus_add1': 'N/A',
                'cus_add2': 'N/A',
                'cus_city': 'N/A',
                'cus_state': 'N/A',
                'cus_postcode': '1000',
                'cus_country': 'Bangladesh',
                'cus_phone': 'N/A',
                'cus_fax': '',
                'ship_name': f"{order.buyer.first_name} {order.buyer.last_name}".strip() or order.buyer.email,
                'ship_add1': 'N/A',
                'ship_add2': 'N/A',
                'ship_city': 'N/A',
                'ship_state': 'N/A',
                'ship_postcode': '1000',
                'ship_country': 'Bangladesh',
                'value_a': str(order.id),
                'value_b': payment.get('payment_uuid', 'N/A'),
                'value_c': order.order_number,
                'value_d': order.service.title[:50],
                'ipn_url': self.ipn_url,
            }
            
            # Generate hash
            payment_data['hash'] = self.generate_hash(payment_data)
            
            # Make API call to SSLCommerz
            response = requests.post(
                f"{self.base_url}/gwprocess/v4/api.php",
                data=payment_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'SUCCESS':
                    # Update payment with session data
                    payment.sslcommerz_session_key = result.get('sessionkey', '')
                    payment.sslcommerz_tran_id = tran_id
                    payment.status = 'processing'
                    payment.gateway_response = result
                    payment.save()
                    
                    return {
                        'success': True,
                        'redirect_url': result.get('GatewayPageURL'),
                        'session_key': result.get('sessionkey'),
                        'tran_id': tran_id
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('failedreason', 'Payment session creation failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP Error: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, payment_data):
        """Verify payment with SSLCommerz"""
        try:
            # Prepare verification data
            verify_data = {
                'store_id': self.store_id,
                'store_passwd': self.store_password,
                'val_id': payment_data.get('val_id'),
                'format': 'json'
            }
            
            # Make API call to verify payment
            response = requests.post(
                f"{self.base_url}/validator/api/validationserverAPI.php",
                data=verify_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'VALID':
                    return {
                        'success': True,
                        'payment_data': result
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'Payment verification failed')
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP Error: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_payment_methods(self):
        """Get available payment methods from SSLCommerz"""
        return {
            'cards': {
                'visa': {
                    'name': 'Visa',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/visa.png',
                    'gateways': ['sslcommerz']
                },
                'mastercard': {
                    'name': 'Mastercard',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/mastercard.png',
                    'gateways': ['sslcommerz']
                },
                'amex': {
                    'name': 'American Express',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/amex.png',
                    'gateways': ['sslcommerz']
                }
            },
            'mobile_banking': {
                'bkash': {
                    'name': 'bKash',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/bkash.png',
                    'gateway': 'sslcommerz'
                },
                'nagad': {
                    'name': 'Nagad',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/nagad.png',
                    'gateway': 'sslcommerz'
                },
                'rocket': {
                    'name': 'Rocket',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/rocket.png',
                    'gateway': 'sslcommerz'
                }
            },
            'internet_banking': {
                'city': {
                    'name': 'City Bank',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/city.png',
                    'gateway': 'sslcommerz'
                },
                'dutch': {
                    'name': 'Dutch Bangla Bank',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/dutch.png',
                    'gateway': 'sslcommerz'
                },
                'brac': {
                    'name': 'BRAC Bank',
                    'logo': 'https://www.sslcommerz.com/wp-content/uploads/2019/01/brac.png',
                    'gateway': 'sslcommerz'
                }
            }
        }
