# 🔭 Observability Lab — 나만의 관제 시스템

> **"장애를 *보기만* 하는 게 답답해서, 감지하고 알려주고 스스로 고치는 관제 시스템을 직접 만들었다."**
>
> 통합관제센터에서 IT 관제 OP로 일하며 느낀 갈증에서 출발한 프로젝트.
> 장애를 *관찰*하는 사람에서, 장애를 *감지·통지·자동 대응하는 시스템을 만드는* 사람으로.

---

## 이 프로젝트가 하는 일

로컬 Docker 환경에서 **감시 대상 앱 → 메트릭 수집 → 시각화 → 로그 수집 → 알림 → 자동 복구**까지,
운영 관측성(Observability)의 전체 흐름을 직접 구축하고 장애 상황을 재현·회고한 랩(lab)이다.

- 📊 **메트릭 & 대시보드** — 요청 수 / 에러율 / 응답시간을 실시간 시각화
- 🔔 **알림** — 임계치 초과 시 디스코드로 자동 통지 (문제 발생 / 복구됨 분기)
- 📝 **로그 수집** — 앱 로그를 중앙에서 조회
- 🩹 **자동 복구(Auto-healing)** — 앱이 죽거나 아프면 **사람 개입 없이** 스스로 재시작
- 🧨 **장애 재현 & 회고** — 의도적으로 장애를 일으키고 postmortem으로 기록

---

## 아키텍처

```
                        ┌─────────────────────────────────────┐
                        │         Docker Compose (7 컨테이너)    │
                        │                                       │
   HTTP 요청 ──────────▶│  ┌─────────┐   scrape   ┌──────────┐  │
                        │  │   app   │◀───────────│prometheus│  │
                        │  │(FastAPI)│  /metrics   └────┬─────┘  │
                        │  └────┬────┘                  │ 알림   │
                        │       │ 로그                   ▼        │
                        │  ┌────▼─────┐  ┌──────┐  ┌──────────┐ │
                        │  │ promtail │─▶│ loki │  │alertmanager│─┼──▶ 💬 Discord
                        │  └──────────┘  └───┬──┘  └──────────┘ │
                        │                    │                   │
                        │  ┌──────────┐  ┌───▼────┐  ┌─────────┐ │
                        │  │ autoheal │  │grafana │  │  (감시)  │ │
                        │  │ (감시자) │  │(대시보드)│           │ │
                        │  └──────────┘  └────────┘             │
                        └─────────────────────────────────────┘
```

| 컨테이너 | 역할 | 포트 |
|---|---|---|
| `app` | 감시 대상 FastAPI 앱 | 8000 |
| `prometheus` | 메트릭 수집 · 알림 판단 | 9090 |
| `grafana` | 시각화 대시보드 | 3000 |
| `loki` | 로그 저장소 | 3100 |
| `promtail` | 로그 수집기 | — |
| `alertmanager` | 경고 통지 (Discord) | 9093 |
| `autoheal` | unhealthy 컨테이너 자동 재시작 | — |

---

## 🩹 자동 복구 (Auto-healing)

핵심 설계는 **"고장은 한 종류가 아니다"**라는 인식이다. 앱이 고장 나는 방식은 두 가지이고,
감지·복구 방법이 각각 다르다.

| 고장 종류 | 겉보기 | 감지 | 복구 |
|---|---|---|---|
| **죽음** — 프로세스 종료 | `docker ps`에 안 보임 | 도커 데몬 | `restart: unless-stopped` |
| **아픔** — 살았는데 응답 불량 | `Up`으로 멀쩡히 보임 | `healthcheck` (10s) | `autoheal` 감시자 (5s) |

관찰(healthcheck)과 조치(autoheal)를 **분리된 두 조각으로 직접 연결**했다.
이는 Kubernetes의 liveness probe가 내부적으로 합쳐 제공하는 기능을,
컨테이너 조합만으로 손수 구현한 것이다.

장애 주입(fault injection)으로 검증 — `POST /break-health`로 앱을 아프게 만든 뒤,
사람이 고치지 않아도 스스로 회복하는 것을 확인했다. 자세한 내용은
[postmortem #2](./postmortem-02-auto-healing.md) 참고.

---

## 🧨 장애 대응 회고 (Postmortem)

실제 SRE 업무의 핵심인 "장애 회고"를 직접 작성하며, 관측의 사각지대를 발견하고 개선했다.

- **[#1 서비스 완전 다운](./postmortem-01-service-down.md)** — 죽은 앱은 에러율로 감지 불가 →
  `up == 0` 기반 `AppDown` 알림 추가
- **[#2 자동 복구 구축과 카오스 검증](./postmortem-02-auto-healing.md)** — 죽음/아픔 두 고장을
  나눠 자동 복구, 그 과정의 함정과 한계 기록

---

## 🚀 실행 방법

```bash
# 1. 저장소 클론
git clone https://github.com/CrestBull/my-observability-lab.git
cd my-observability-lab

# 2. 디스코드 웹훅 설정 (비밀값 — 아래 참고)
cp discord_webhook.txt.example discord_webhook.txt
#   → discord_webhook.txt를 열어 실제 웹훅 URL로 교체

# 3. 전체 스택 실행 (7개 컨테이너)
docker compose up -d

# 4. 접속
#   앱          http://localhost:8000
#   Grafana     http://localhost:3000  (admin / admin)
#   Prometheus  http://localhost:9090
#   Alertmanager http://localhost:9093
```

### 앱 엔드포인트

| 경로 | 설명 |
|---|---|
| `/health` | 헬스체크 (자동복구 프로브 대상) |
| `/api/data` | 정상 트래픽 |
| `/slow` | 1~3초 지연 (지연 실험) |
| `/break` | 20% 확률 500 에러 (에러율 실험) |
| `/break-health` · `/fix-health` | 장애 주입 스위치 (자동복구 검증용) |
| `/metrics` | Prometheus 메트릭 (자동 노출) |

---

## 🔐 비밀값 관리

디스코드 웹훅 URL 같은 비밀값은 **저장소에 커밋하지 않는다.**

- 실제 URL은 `discord_webhook.txt`에만 존재 → `.gitignore`로 제외
- 설정 파일(`alertmanager.yml`)에는 URL 대신 파일 경로(`webhook_url_file`)만 참조
- 견본(`discord_webhook.txt.example`)만 저장소에 포함

> ⚠️ `autoheal`은 `/var/run/docker.sock`을 마운트한다(호스트 루트급 권한).
> 로컬 실습 전용이며, 운영 환경에선 별도 보안 처리가 필요하다.

---

## 🛠️ 기술 스택

`Docker` · `Docker Compose` · `FastAPI` · `Prometheus` · `Grafana` · `Loki` · `Promtail` ·
`Alertmanager` · `willfarrell/autoheal`

---

## 🗺️ 로드맵

- [x] **Week 1–2** — 앱 컨테이너화 + Prometheus/Grafana 대시보드
- [x] **Week 3** — Loki 로그 수집 + Alertmanager 디스코드 알림
- [x] **Week 4** — 장애 재현 & 회고 (#1)
- [x] **Week 5 (1단계)** — 자동 복구(Auto-healing) + 카오스 검증 (#2)
- [ ] **Week 5 (이후)** — IaC(Terraform) · AWS 배포 · CI/CD(GitHub Actions)
- [ ] **여력** — Kubernetes

---

*관제 OP → MSP → SRE 로 가는 길목에서 만든 앵커 프로젝트.*
