import logging     
import random           
import time             

from fastapi import FastAPI, HTTPException, Response         
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator  


logging.basicConfig(
    level=logging.INFO,                                  
    format="%(asctime)s | %(levelname)s | %(message)s",  
)
logger = logging.getLogger("lab-app")                    

app = FastAPI(title="Observability Lab App")             


Instrumentator().instrument(app).expose(app)



_is_healthy = True

@app.get("/health")
def health():
    if _is_healthy:
        return {"status": "ok"}
    # 아픔 상태: 503을 반환 → healthcheck의 urlopen이 예외를 던짐 → 도커가 unhealthy로 판정
    return Response(content='{"status": "sick"}', status_code=503, media_type="application/json")

@app.post("/break-health")
def break_health():
    global _is_healthy
    _is_healthy = False
    return {"health": "now BROKEN — 앱이 아픈 척합니다"}

@app.post("/fix-health")
def fix_health():
    global _is_healthy
    _is_healthy = True
    return {"health": "now OK — 앱이 나았습니다"}


@app.get("/api/data")        # [내가 정함] 정상 트래픽 역할 경로
def get_data():
    logger.info("GET /api/data - 정상 요청 처리")   # [내가 정함] INFO 로그
    return {
        "items": [{"id": i, "value": random.randint(1, 100)} for i in range(5)],
        "served_at": time.time(),
    }


@app.get("/slow")            # [내가 정함] 지연 실험용 경로
def slow():
    delay = random.uniform(1.0, 3.0)   # [내가 정함] 1~3초 랜덤 지연
    logger.warning(f"GET /slow - {delay:.2f}초 지연 발생")  # [내가 정함] WARNING 로그
    time.sleep(delay)                  # [내가 정함] 일부러 멈춤
    return {"message": f"{delay:.2f}초 걸려서 응답했어요", "delay": delay}


@app.get("/break")           # [내가 정함] 장애 실험용 경로
def break_it():
    if random.random() < 0.2:          # [내가 정함] 20% 확률로 실패 (임계치는 내 마음대로)
        logger.error("GET /break - 의도된 장애 발생! (500)")  # [내가 정함] ERROR 로그
        raise HTTPException(status_code=500, detail="의도적으로 터뜨린 에러입니다")
        #     [라이브러리] raise HTTPException → HTTP 500 응답으로 변환됨. 500은 [관례] 서버 에러 코드.
    logger.info("GET /break - 이번엔 무사히 통과")
    return {"message": "운 좋게 살아남았습니다 (80% 확률)"}


@app.get("/")                # [내가 정함] 접속 확인용 안내 페이지
def root():
    return JSONResponse(
        {
            "app": "Observability Lab",
            "try": ["/health", "/api/data", "/slow", "/break", "/metrics"],
        }
    )
