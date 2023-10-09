from functools import lru_cache

import docusign_esign
from humps import depascalize

from app.esign.schema.envelope import TabsRequest
from app.esign.schema.radio_tab import DSRadioGroupTab
from app.esign.schema.tab_fields import DSAbstractTab


def build_esign_tabs(request_tabs: TabsRequest | None) -> docusign_esign.Tabs | None:
    if request_tabs is None:
        return None

    # Every DocuSign Tab class inherits from object
    ds_tabs: dict[str, list[object]] = {}

    tab_schemas: list[DSAbstractTab]
    for field_name, tab_schemas in request_tabs:
        if not tab_schemas:
            continue

        for tab_schema in tab_schemas:
            ds_tabs_argument = depascalize(field_name)
            ds_tab = tab_schema.to_ds_tab()

            if isinstance(tab_schema, DSRadioGroupTab):
                ds_tab.radios = [radio_schema.to_ds_tab() for radio_schema in tab_schema.radios]

            ds_tabs.setdefault(ds_tabs_argument, []).append(ds_tab)

    return docusign_esign.Tabs(**ds_tabs)


@lru_cache
def build_event_notification(webhook_url: str | None) -> docusign_esign.EventNotification | None:
    if webhook_url is None:
        return None

    false_statement = "false"
    true_statement = "true"

    return docusign_esign.EventNotification(
        url=webhook_url,
        event_data=docusign_esign.ConnectEventData(
            format="",
            version="restv2.1",
            include_data=[
                "extensions",
                "recipients",
                "attachments",
            ]
        ),
        logging_enabled=true_statement,
        require_acknowledgment=true_statement,
        use_soap_interface=false_statement,
        include_certificate_with_soap=false_statement,
        sign_message_with_x509_cert=false_statement,
        include_documents=true_statement,
        include_envelope_void_reason=true_statement,
        include_time_zone=true_statement,
        include_sender_account_as_custom_field=true_statement,
        include_document_fields=true_statement,
        include_certificate_of_completion=true_statement,
        include_o_auth=true_statement,
        envelope_events=[
            docusign_esign.EnvelopeEvent(
                envelope_event_status_code=event_status_code,
                include_documents=false_statement
            )
            for event_status_code in ("Sent", "Delivered", "Completed", "Declined", "Voided")
        ],
        recipient_events=[
            docusign_esign.RecipientEvent(
                recipient_event_status_code=event_status_code,
                include_documents=false_statement
            )
            for event_status_code in (
                "Sent", "AutoResponded", "Delivered", "Completed", "Declined", "AuthenticationFailed", "FinishLater"
            )
        ]
    )
