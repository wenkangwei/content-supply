"""Notification service — Webhook / Email for cleanup review."""

import json
import logging
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    """Send review notifications via webhook or email."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        auto_confirm_hours: int = 24,
    ):
        self.webhook_url = webhook_url
        self.auto_confirm_hours = auto_confirm_hours

    async def send_review_notification(self, cleanup_log: dict) -> bool:
        """Send a review notification for a pending cleanup.

        Args:
            cleanup_log: dict with id, policy, source_type, items_to_delete,
                        pending_item_ids, auto_confirm_at, etc.

        Returns True if notification was sent successfully.
        """
        if not self.webhook_url:
            logger.info("No webhook URL configured, skipping notification")
            return False

        # Build notification payload
        item_ids = json.loads(cleanup_log.get("pending_item_ids", "[]"))
        sample_ids = item_ids[:10] if isinstance(item_ids, list) else []

        payload = {
            "type": "cleanup_review",
            "cleanup_id": cleanup_log["id"],
            "policy": cleanup_log["policy"],
            "source_type": cleanup_log["source_type"],
            "items_to_delete": cleanup_log["items_to_delete"],
            "items_scanned": cleanup_log.get("items_scanned", 0),
            "sample_item_ids": sample_ids,
            "auto_confirm_at": str(cleanup_log.get("auto_confirm_at", "")),
            "review_url": f"/api/cleanup/{cleanup_log['id']}",
            "confirm_action": f"POST /api/cleanup/{cleanup_log['id']}/confirm",
            "reject_action": f"POST /api/cleanup/{cleanup_log['id']}/reject",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code < 400:
                    logger.info(
                        f"Review notification sent for cleanup {cleanup_log['id']}: "
                        f"{cleanup_log['items_to_delete']} items pending"
                    )
                    return True
                else:
                    logger.warning(
                        f"Webhook returned {resp.status_code}: {resp.text[:200]}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Failed to send review notification: {e}")
            return False

    async def send_dingtalk(self, token: str, cleanup_log: dict) -> bool:
        """Send notification via DingTalk robot webhook."""
        url = f"https://oapi.dingtalk.com/robot/send?access_token={token}"
        item_ids = json.loads(cleanup_log.get("pending_item_ids", "[]"))

        text = (
            f"## 内容清理审核通知\n\n"
            f"- **清理策略**: {cleanup_log['policy']}\n"
            f"- **数据源类型**: {cleanup_log['source_type']}\n"
            f"- **待删数量**: {cleanup_log['items_to_delete']}\n"
            f"- **涉及ID**: {len(item_ids)} 条\n"
            f"- **自动确认时间**: {cleanup_log.get('auto_confirm_at', 'N/A')}\n\n"
            f"> 请在自动确认前审核确认或拒绝"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "msgtype": "markdown",
                "markdown": {"title": "内容清理审核", "text": text},
            })
            return resp.status_code == 200

    async def send_feishu(self, webhook_key: str, cleanup_log: dict) -> bool:
        """Send notification via Feishu/Lark robot webhook."""
        url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{webhook_key}"
        item_ids = json.loads(cleanup_log.get("pending_item_ids", "[]"))

        content = (
            f"内容清理审核通知\n"
            f"策略: {cleanup_log['policy']} | 源: {cleanup_log['source_type']}\n"
            f"待删: {cleanup_log['items_to_delete']} 条\n"
            f"自动确认: {cleanup_log.get('auto_confirm_at', 'N/A')}\n"
            f"请及时审核"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "msg_type": "text",
                "content": {"text": content},
            })
            return resp.status_code < 400

    async def send_wechat(self, webhook_key: str, cleanup_log: dict) -> bool:
        """Send notification via WeCom (企业微信) robot webhook."""
        url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
        item_ids = json.loads(cleanup_log.get("pending_item_ids", "[]"))

        content = (
            f"【内容清理审核】\n"
            f"策略: {cleanup_log['policy']}\n"
            f"数据源: {cleanup_log['source_type']}\n"
            f"待删数量: {cleanup_log['items_to_delete']}\n"
            f"请及时审核确认"
        )

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "msgtype": "text",
                "text": {"content": content},
            })
            return resp.status_code < 400
