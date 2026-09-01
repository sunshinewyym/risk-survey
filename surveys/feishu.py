import base64
import hashlib
import hmac
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone


def _signature(secret):
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(string_to_sign.encode(), digestmod=hashlib.sha256).digest()
    return timestamp, base64.b64encode(digest).decode()


def _message(registration):
    attendees = "、".join(
        f"{person.name}（{person.role}，{person.phone}）"
        for person in registration.attendees.all()
    )
    issues = "\n".join(registration.priority_issue_labels())
    submitted_at = timezone.localtime(registration.submitted_at).strftime("%Y-%m-%d %H:%M:%S")
    return (
        "【活动报名提醒】\n"
        f"公司：{registration.company_name}\n"
        f"联系人：{registration.contact_name} {registration.contact_phone}\n"
        f"城市：{registration.city}\n"
        f"参会人员：{attendees}\n"
        f"合作项目：{registration.get_project_count_display()}\n"
        f"涉诉/追索：{registration.get_lawsuit_count_display()}\n"
        f"重点问题：\n{issues}\n"
        f"了解渠道：{registration.get_source_channel_display()}\n"
        f"提交时间：{submitted_at}"
    )


def send_registration_notification(registration):
    webhook = settings.FEISHU_WEBHOOK_URL.strip()
    if not webhook:
        return False, "未配置飞书 Webhook"

    payload = {"msg_type": "text", "content": {"text": _message(registration)}}
    if settings.FEISHU_WEBHOOK_SECRET:
        timestamp, sign = _signature(settings.FEISHU_WEBHOOK_SECRET)
        payload.update({"timestamp": timestamp, "sign": sign})

    request = Request(
        webhook,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        if result.get("code", result.get("StatusCode", 0)) != 0:
            return False, str(result.get("msg") or result.get("StatusMessage") or "飞书返回错误")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, f"发送失败：{exc}"
    return True, ""
