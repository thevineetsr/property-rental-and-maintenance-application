import os
import requests
from typing import Optional, Dict, Any, List
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000") + "/api"


class ApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"[{status_code}] {detail}")


class ApiClient:
    """HTTP client wrapper that handles JWT authentication and API requests."""

    @staticmethod
    def _headers(token: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        active_token = token or st.session_state.get("token")
        if active_token:
            headers["Authorization"] = f"Bearer {active_token}"
        return headers

    @staticmethod
    def _handle_response(response: requests.Response) -> Any:
        if response.status_code >= 400:
            try:
                data = response.json()
                detail = data.get("detail", response.text)
                if isinstance(detail, list):
                    # Pydantic validation error list
                    detail = "; ".join([f"{err.get('loc', [''])[ -1]}: {err.get('msg', '')}" for err in detail])
            except Exception:
                detail = response.text or f"HTTP {response.status_code}"
            raise ApiError(response.status_code, detail)
        
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text

    # --- Auth ---
    @classmethod
    def login(cls, email: str, password: str) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/auth/login"
        res = requests.post(url, json={"email": email, "password": password})
        return cls._handle_response(res)

    @classmethod
    def register(cls, email: str, password: str, full_name: str, role: str) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/auth/register"
        res = requests.post(url, json={"email": email, "password": password, "full_name": full_name, "role": role})
        return cls._handle_response(res)

    @classmethod
    def get_me(cls) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/auth/me"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_contractors(cls) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/auth/contractors"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    # --- Units ---
    @classmethod
    def get_units(cls, include_archived: bool = False) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/units"
        res = requests.get(url, params={"include_archived": include_archived}, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_unit(cls, unit_id: int) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/units/{unit_id}"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def create_unit(cls, unit_number: str, address: str, monthly_rent: float, tenant_name: Optional[str]) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/units"
        payload = {
            "unit_number": unit_number,
            "address": address,
            "monthly_rent": monthly_rent,
            "tenant_name": tenant_name or None
        }
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def update_unit(cls, unit_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/units/{unit_id}"
        res = requests.patch(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def archive_unit(cls, unit_id: int) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/units/{unit_id}/archive"
        res = requests.post(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def restore_unit(cls, unit_id: int) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/units/{unit_id}/restore"
        res = requests.post(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_unit_maintenance(cls, unit_id: int) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/units/{unit_id}/maintenance"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    # --- Rent ---
    @classmethod
    def get_rent_status(cls, month: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/rent/status"
        params = {"month": month} if month else {}
        res = requests.get(url, params=params, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def record_payment(cls, unit_id: int, amount: float, month_covered: str, notes: Optional[str] = None) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/rent/payments"
        payload = {
            "unit_id": unit_id,
            "amount": amount,
            "month_covered": month_covered,
            "notes": notes
        }
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_unit_payments(cls, unit_id: int) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/rent/payments/unit/{unit_id}"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def bulk_record_rent(cls, month_covered: str, payments: List[Dict[str, Any]]) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/rent/bulk"
        payload = {"month_covered": month_covered, "payments": payments}
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_rent_roll_csv(cls, month: Optional[str] = None) -> str:
        url = f"{API_BASE_URL}/rent/roll/csv"
        params = {"month": month} if month else {}
        res = requests.get(url, params=params, headers=cls._headers())
        if res.status_code >= 400:
            cls._handle_response(res)
        return res.text

    @classmethod
    def get_rent_alerts(cls, month: Optional[str] = None) -> List[Dict[str, Any]]:
        url = f"{API_BASE_URL}/rent/alerts"
        params = {"month": month} if month else {}
        res = requests.get(url, params=params, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def dismiss_rent_alert(cls, unit_id: int, month_covered: str) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/rent/alerts/{unit_id}/dismiss"
        res = requests.post(url, json={"month_covered": month_covered}, headers=cls._headers())
        return cls._handle_response(res)

    # --- Maintenance ---
    @classmethod
    def get_maintenance_requests(
        cls,
        query: Optional[str] = None,
        unit_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        contractor_id: Optional[int] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance"
        params: Dict[str, Any] = {
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "page_size": page_size
        }
        if query:
            params["query"] = query
        if unit_id:
            params["unit_id"] = unit_id
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        if contractor_id:
            params["contractor_id"] = contractor_id

        res = requests.get(url, params=params, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_maintenance_request(cls, request_id: int) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance/{request_id}"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def create_maintenance_request(cls, unit_id: int, description: str, priority: str) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance"
        payload = {"unit_id": unit_id, "description": description, "priority": priority}
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def update_maintenance_details(cls, request_id: int, description: Optional[str] = None, priority: Optional[str] = None) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance/{request_id}"
        payload = {}
        if description is not None:
            payload["description"] = description
        if priority is not None:
            payload["priority"] = priority
        res = requests.patch(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def update_maintenance_status(cls, request_id: int, status: str, note: Optional[str] = None) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance/{request_id}/status"
        payload = {"status": status, "note": note}
        res = requests.patch(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def assign_contractors(cls, request_id: int, contractor_ids: List[int]) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance/{request_id}/contractors"
        payload = {"contractor_ids": contractor_ids}
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def add_maintenance_note(cls, request_id: int, note: str) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/maintenance/{request_id}/notes"
        payload = {"note": note}
        res = requests.post(url, json=payload, headers=cls._headers())
        return cls._handle_response(res)

    # --- Dashboard ---
    @classmethod
    def get_manager_dashboard(cls) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/dashboard/manager"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)

    @classmethod
    def get_contractor_dashboard(cls) -> Dict[str, Any]:
        url = f"{API_BASE_URL}/dashboard/contractor"
        res = requests.get(url, headers=cls._headers())
        return cls._handle_response(res)
