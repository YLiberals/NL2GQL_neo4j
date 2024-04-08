# Embedding config
EMBEDDING_BATCH_NUM=10
EMBEDDING_MODEL='m3e-base'
NODE_CSV_PATH= 'dataset/entities.csv'


# Vector_store config
DISTANCE_STRATEGY="EUCLIDEAN_DISTANCE"
NORMALIZE_L2=False
TOP_K=1

# Smaller_LLM config
SLLM_MODEL_NAME='Qwen-7B-Chat'
SLLM_MODEL_PATH='./Qwen-7B-Chat/'
LORA_PATH=''
API_URL=''
DEVICE_MAP='auto'
USE_LORA=False
USE_API=False


# Bigger_LLM config
OPENAI_API_BASE = "https://api.openai.com/v1"
OPENAI_API_MODEL= "gpt-4"
# MAX_TOKENS=4000 if OPENAI_API_MODEL!='gpt-4' else 8000
OPENAI_API_KEY= "your key"


#Nebula config

MAX_CONNECTION_POOL_SIZE=10
USERNAME='root'
PASSWORD='nebula'





