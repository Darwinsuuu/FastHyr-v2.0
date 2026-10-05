import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# SCREEN_SPECS.md S-01, in the order the API checks them.
InterviewLinkState = Literal[
    "unavailable",
    "expired",
    "sign_in",
    "wrong_account",
    "completed",
    "technical_problem",
    "resume",
    "welcome",
]


class InterviewCompany(BaseModel):
    name: str
    logo_url: str | None
    website: str | None
    careers_url: str | None


class InterviewLink(BaseModel):
    """What the interview link page shows (INTV-002). Personal details (`first_name`) appear only
    once the signed-in account is the one that applied; never a stage, score or flag."""

    state: InterviewLinkState
    company: InterviewCompany
    job_title: str
    format: Literal["video_voice", "voice_only"]
    expires_at: datetime
    expires_label: str = Field(
        description="The expiry as the invitation email writes it, in the company's time zone"
    )
    first_name: str | None = Field(
        default=None, description="Only for the account that applied (not sign_in/wrong_account)"
    )
    masked_email: str | None = Field(
        default=None, description="Only on sign_in: the applying account, e.g. p•••@gmail.com"
    )
    minutes_left: int | None = Field(
        default=None, description="Only on resume: what is left of the 30-minute cap"
    )
    face_check: bool = Field(
        description=(
            "Video interview with integrity checks on: the device check asks for the biometric "
            "consent too (S-01, ADR-016)"
        )
    )


class InterviewConsentRequest(BaseModel):
    """The device check's consent (INTV-003, FR-INTV-03): the notice ids the candidate agreed
    to, from `GET /v1/public/notices`."""

    consent_notice_id: str = Field(
        max_length=64, description="The interview notice, e.g. interview@v1"
    )
    biometric_notice_id: str | None = Field(
        default=None,
        max_length=64,
        description="The biometric notice (e.g. biometric@v1); required when `face_check`",
    )


class InterviewConsent(BaseModel):
    """What the interview now records (PRIVACY.md §3)."""

    consent_version: str
    consent_at: datetime
    biometric_consent_version: str | None


class InterviewSessionRequest(BaseModel):
    """Starts or resumes the live interview (INTV-004): the browser's WebRTC offer."""

    sdp: str = Field(
        min_length=1,
        max_length=65536,
        description="The RTCPeerConnection's SDP offer (microphone track, data channel)",
    )


class InterviewTopic(BaseModel):
    number: int = Field(description="1 is the first topic; set_topic tool calls use it")
    title: str


class InterviewSession(BaseModel):
    """What the browser needs to finish the connection and run the interview UI."""

    attempt_id: uuid.UUID
    sdp: str = Field(description="OpenAI's SDP answer, for setRemoteDescription")
    time_left_seconds: int = Field(description="What is left of the 30-minute cap")
    wrap_up_in_seconds: int = Field(description="When the interviewer starts wrapping up")
    heartbeat_seconds: int = Field(description="How often to call …/heartbeat")
    topics: list[InterviewTopic]
    topic_number: int = Field(description="The topic this attempt starts from")


EndReason = Literal["candidate_ended", "wrap_up", "time_cap", "disconnect", "error"]


class InterviewHeartbeatRequest(BaseModel):
    attempt_id: uuid.UUID
    connected: bool = Field(description="The peer connection is up (connectionState connected)")


class InterviewHeartbeat(BaseModel):
    """`ended` means the session is over: the browser closes its connection and asks the link
    page what to show next."""

    status: Literal["active", "wrap_up", "ended"]
    time_left_seconds: int
    end_reason: EndReason | None = None


class InterviewCompleteRequest(BaseModel):
    attempt_id: uuid.UUID | None = Field(
        default=None, description="The attempt the candidate ended, when one is running"
    )


class InterviewCompleted(BaseModel):
    status: Literal["completed"]
    talk_seconds: int


# --- Recording (INTV-006) ---------------------------------------------------------------------

RecordingType = Literal["webm", "mp4"]

# 5-second chunks for 30 minutes are 360; the rest is room for a slower timeslice.
MAX_CHUNK_SEQ = 2000
CHUNK_URL_BATCH = 30


class RecordingChunkUrlsRequest(BaseModel):
    attempt_id: uuid.UUID
    type: RecordingType = Field(description="The recorder's container: WebM, or MP4 (Safari)")
    from_seq: int = Field(ge=0, lt=MAX_CHUNK_SEQ, description="The first chunk number wanted")
    count: int = Field(ge=1, le=CHUNK_URL_BATCH)


class RecordingChunkUrl(BaseModel):
    seq: int
    url: str = Field(description="Signed upload URL: PUT the chunk's bytes once")


class RecordingChunkUrls(BaseModel):
    urls: list[RecordingChunkUrl]


class RecordingChunkRequest(BaseModel):
    attempt_id: uuid.UUID
    seq: int = Field(ge=0, lt=MAX_CHUNK_SEQ)
    last: bool = Field(
        default=False, description="The attempt's recorder stopped: no chunk comes after this one"
    )


class RecordingChunkRegistered(BaseModel):
    seq: int
    bytes: int
