import azure.functions as func
import logging, json, os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Azure OpenAI & Azure AI Search 환경변수 설정
AZURE_AISEARCH_NAME = os.environ["AZURE_AISEARCH_NAME"]
AZURE_AISEARCH_INDEX_NAME = os.environ["AZURE_AISEARCH_INDEX_NAME"]
AZURE_AISEARCH_KEY = os.environ["AZURE_AISEARCH_KEY"]

AZURE_OPENAI_VERSION = os.environ["AZURE_OPENAI_VERSION"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_KEY = os.environ["AZURE_OPENAI_KEY"]

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        query = req_body.get('query')

        # Azure AI Search 클라이언트 생성
        search_endpoint = f"https://{AZURE_AISEARCH_NAME}.search.windows.net"
        search_credential = AzureKeyCredential(AZURE_AISEARCH_KEY)
        search_client = SearchClient(endpoint=search_endpoint, index_name=AZURE_AISEARCH_INDEX_NAME, credential=search_credential)

        # 인덱스에서 검색 실행
        search_results = search_client.search(search_text=query, top=5)

        # 검색 결과 처리
        context = ""
        for search_result in search_results:
            context += "".join(search_result.get("chunk", "")) + " "

        # Azure OpenAI 클라이언트 생성
        openai_client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_KEY,
            api_version=AZURE_OPENAI_VERSION
        )

        # 프롬프트 설정
        prompt = f"""
            컨텍스트: {context}
            질문: {query}
            답변:
        """.replace("\n", " ").strip()

        # 검색 결과를 참고하여 생성형 답변 생성
        response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # JSON 응답 생성
        result = {
            "prompt": prompt,
            "response": response.choices[0].message.content
        }
        
        return func.HttpResponse(
            body=json.dumps(result, ensure_ascii=False),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        return func.HttpResponse(
            "An error occurred while processing the request.",
            status_code=500
        )