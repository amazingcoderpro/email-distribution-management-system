import hashlib, base64, hmac


def get_hmac(body, secret):
    """
    Calculate the HMAC value of the given request body and secret as per Shopify's documentation for Webhook requests.
    See: http://docs.shopify.com/api/tutorials/using-webhooks#verify-webhook
    """
    hash = hmac.new(secret.encode('utf-8'), body, hashlib.sha256)
    return base64.b64encode(hash.digest()).decode()

