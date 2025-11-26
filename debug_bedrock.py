import os
import traceback
import boto3
import botocore

print('AWS_REGION=', os.environ.get('AWS_REGION'))
print('AWS_ACCESS_KEY_ID=', 'present' if os.environ.get('AWS_ACCESS_KEY_ID') else 'missing')
print('boto3', boto3.__version__, 'botocore', botocore.__version__)

try:
    sess = boto3.session.Session()
    services = sess.get_available_services()
    print('available services sample:', ','.join(services[:30]))
except Exception:
    traceback.print_exc()


def try_client(name):
    try:
        client = boto3.client(name)
        print(f'{name} client created')
        return client
    except Exception:
        print(f'Error creating client {name}:')
        traceback.print_exc()
        return None

bedrock_runtime_client = try_client('bedrock-runtime')
bedrock_client = try_client('bedrock')
sts_client = try_client('sts')

if sts_client:
    try:
        print('sts identity:', sts_client.get_caller_identity())
    except Exception:
        traceback.print_exc()