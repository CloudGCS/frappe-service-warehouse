import frappe


class APIResponse:
    def __init__(self, data=None, message="Success", status="success", status_code=200):
        """
        Standard API response helper class.

        :param data: dict or list containing the response data
        :param message: message string
        :param status: "success" or "failed"
        :param status_code: HTTP status code (200, 400, 404, 500, etc.)
        """
        self.data = data
        self.message = message
        self.status = status
        self.status_code = status_code

    def as_dict(self):
        """
        Returns a dictionary ready to return from a Frappe controller
        and sets the HTTP status code.
        """
        frappe.local.response["http_status_code"] = self.status_code
        return {"status": self.status, "message": self.message, "data": self.data}

    @staticmethod
    def success(data=None, message="Success"):
        return APIResponse(
            data=data, message=message, status="success", status_code=200
        ).as_dict()

    @staticmethod
    def failed(message="Failed", status_code=400, data=None):
        return APIResponse(
            data=data, message=message, status="failed", status_code=status_code
        ).as_dict()
