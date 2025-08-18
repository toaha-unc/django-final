from freelancer_platform.wsgi import application

# Vercel serverless function handler
def handler(request, context):
    return application(request, context)
