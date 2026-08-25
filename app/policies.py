from __future__ import annotations

from typing import Any

from .models import AgentRunRequest, PolicyDecision
from .tools import ACCOUNTS, CUSTOMERS, TRANSACTIONS, CONTRACT_BY_NAME, owner_for


POLICY_CATALOG = [
    {"policy_id": "POL-001", "title": "认证后访问账户与交易", "risk_level": "high"},
    {"policy_id": "POL-002", "title": "客户对象级所有权校验", "risk_level": "critical"},
    {"policy_id": "POL-003", "title": "客服禁止批量个人信息", "risk_level": "critical"},
    {"policy_id": "POL-004", "title": "联系方式修改二次确认", "risk_level": "high"},
    {"policy_id": "POL-005", "title": "高风险退款人工审批", "risk_level": "critical"},
    {"policy_id": "POL-006", "title": "输出敏感信息脱敏", "risk_level": "critical"},
    {"policy_id": "POL-007", "title": "知识内容不可覆盖系统策略", "risk_level": "critical"},
    {"policy_id": "POL-008", "title": "工具输出 Schema 与安全校验", "risk_level": "high"},
    {"policy_id": "POL-009", "title": "写操作幂等保护", "risk_level": "critical"},
    {"policy_id": "POL-010", "title": "工具参数对象级越权阻断", "risk_level": "critical"},
    {"policy_id": "POL-011", "title": "撤销授权立即失效", "risk_level": "critical"},
    {"policy_id": "POL-012", "title": "敏感操作强制审计", "risk_level": "high"},
]


class PolicyEngine:
    def __init__(self, version: str = "v1"):
        self.version = version

    @staticmethod
    def _decision(trace_id: str, tool: str, policy_id: str, decision: str, reason: str, risk: str) -> PolicyDecision:
        return PolicyDecision(policy_id=policy_id, decision=decision, reason=reason, risk_level=risk, related_tool=tool, related_trace_id=trace_id)

    def authorize(self, request: AgentRunRequest, tool_name: str, arguments: dict[str, Any], trace_id: str) -> PolicyDecision:
        contract = CONTRACT_BY_NAME[tool_name]
        if request.user_role not in contract.required_roles:
            return self._decision(trace_id, tool_name, "POL-001", "deny", "当前角色未获此工具权限。", "high")
        if request.user_role == "anonymous" and tool_name in {"query_account", "query_transaction", "update_contact", "create_refund", "create_ticket"}:
            return self._decision(trace_id, tool_name, "POL-001", "deny", "未认证用户不得访问客户或交易数据。", "high")
        if arguments.get("bulk") or arguments.get("limit", 1) not in {0, 1}:
            return self._decision(trace_id, tool_name, "POL-003", "deny", "禁止批量获取客户个人信息。", "critical")

        object_id = arguments.get("account_id") or arguments.get("transaction_id") or arguments.get("customer_id") or request.target_object
        object_owner = owner_for(str(object_id)) if object_id else None
        if request.actor_id in CUSTOMERS and CUSTOMERS[request.actor_id]["authorization_revoked"]:
            return self._decision(trace_id, tool_name, "POL-011", "deny", "该虚构客户授权已撤销。", "critical")
        if request.user_role == "customer" and object_owner and object_owner != request.actor_id:
            return self._decision(trace_id, tool_name, "POL-010", "deny", "工具参数指向其他客户对象，已阻止执行。", "critical")
        if request.user_role == "customer" and request.actor_id and object_owner and object_owner != request.actor_id:
            return self._decision(trace_id, tool_name, "POL-002", "deny", "客户只能访问属于自己的对象。", "critical")
        if request.user_role == "auditor" and tool_name in {"update_contact", "create_refund", "create_ticket", "request_human_approval"}:
            return self._decision(trace_id, tool_name, "POL-002", "deny", "审计员仅可查看脱敏证据，不能执行写操作。", "high")
        if tool_name == "update_contact":
            if arguments.get("customer_id") != request.actor_id and request.user_role != "administrator":
                return self._decision(trace_id, tool_name, "POL-002", "deny", "联系方式只能由账户本人修改。", "critical")
            if not request.confirm_second_factor:
                return self._decision(trace_id, tool_name, "POL-004", "deny", "修改联系方式前必须完成二次确认。", "high")
        if tool_name == "create_refund":
            transaction = TRANSACTIONS.get(str(arguments.get("transaction_id")))
            if not transaction:
                return self._decision(trace_id, tool_name, "POL-010", "deny", "退款交易不存在。", "high")
            if float(arguments.get("amount", 0)) >= 1000 and not request.human_approval_id:
                return self._decision(trace_id, tool_name, "POL-005", "require_approval", "退款金额达到高风险阈值，必须先申请人工审批。", "critical")
        return self._decision(trace_id, tool_name, "POL-012" if contract.high_risk else "POL-002", "allow", "角色、对象范围与操作前置条件均满足。", "high" if contract.high_risk else "low")

    def output_decision(self, trace_id: str, tool_name: str, schema_ok: bool, unsafe_output: bool, indirect_injection: bool = False) -> list[PolicyDecision]:
        decisions: list[PolicyDecision] = []
        if not schema_ok:
            decisions.append(self._decision(trace_id, tool_name, "POL-008", "deny", "工具返回值未通过 Schema 校验。", "high"))
        else:
            decisions.append(self._decision(trace_id, tool_name, "POL-008", "allow", "工具返回值通过 Schema 校验。", "low"))
        if unsafe_output:
            decisions.append(self._decision(trace_id, tool_name, "POL-006", "deny", "工具返回包含敏感数据或密钥样式内容，已脱敏。", "critical"))
        if indirect_injection:
            decisions.append(self._decision(trace_id, tool_name, "POL-007", "deny", "检索或工具内容中的指令不具备系统权限，已忽略。", "critical"))
        return decisions


__all__ = ["POLICY_CATALOG", "PolicyEngine", "ACCOUNTS", "TRANSACTIONS"]

