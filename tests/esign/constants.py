from types import MappingProxyType
from typing import cast

MULTIPLIER = 12
EMAIL_SUBJECT = "emailSubject"

_REQUEST_WITH_ALL_TABS = MappingProxyType({
    "emailSubject": "Please sign this document",
    "emailBody": "This body will be ignored by DocuSign, because all signers have their own bodies",
    "documents": [
        {
            "documentId": 1,
            "name": "Main document",
            "bucketName": "bucket_name",
            "documentPath": "templates/esign.pdf"
        }
    ],
    "signers": [
        {
            "recipientId": 1,
            "shouldPauseSigningBefore": False,
            "email": "cesigntest@gmail.com",
            "name": "Odin Borson",
            "order": 1,
            "emailSubject": "Odin Borson, please sign this document",
            "emailBody": "This is the best and the most important document\nfor Signer 1.\n\nBest wishes.",
            "tabs": {
                "initialHereTabs": [
                    {
                     "anchorString": "/sn1/",
                     "anchorUnits": "pixels",
                     "anchorXOffset": 0,
                     "anchorYOffset": 0
                    },
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 230,
                        "yPosition": 160,
                        "tabId": "initialHereTabId1",
                        "tabLabel": "initialHereTabLabel1",
                        "name": "initialHereName1"
                    }
                ],
                "signHereTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 70,
                        "yPosition": 200,
                        "tabId": "signHereTabId1",
                        "tabLabel": "signHereTabLabel1",
                        "name": "signHereName1",
                        "scaleValue": 0.8
                    }
                ],
                "fullNameTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 370,
                        "yPosition": 50,
                        "tabId": "fullNameTabId1",
                        "tabLabel": "fullNameTabLabel1",
                        "name": "fullNameName1",
                        "fontSize": "size14"
                    }
                ],
                "textTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 370,
                        "yPosition": 75,
                        "tabId": "textTabId1",
                        "tabLabel": "textTabLabel1",
                        "name": "textName1",
                        "required": True,
                        "fontSize": "size12",
                        "width": 180,
                        "maxLength": 100
                    },
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 85,
                        "yPosition": 575,
                        "tabId": "textTabId2",
                        "tabLabel": "textTabLabel2",
                        "name": "textName2",
                        "required": True,
                        "fontSize": "size9",
                        "value": "Check to see number field",
                        "locked": True
                    },
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 365,
                        "yPosition": 575,
                        "tabId": "textTabId3",
                        "tabLabel": "textTabLabel3",
                        "name": "textName3",
                        "required": True,
                        "fontSize": "size9",
                        "value": "First radio option",
                        "locked": True
                    },
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 365,
                        "yPosition": 600,
                        "tabId": "textTabId4",
                        "tabLabel": "textTabLabel4",
                        "name": "textName4",
                        "required": True,
                        "fontSize": "size9",
                        "value": "Second radio option",
                        "locked": True
                    }
                ],
                "emailTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 370,
                        "yPosition": 100,
                        "tabId": "emailTabId1",
                        "tabLabel": "emailTabLabel1",
                        "name": "emailName1",
                        "required": True,
                        "fontSize": "size11",
                        "width": 180,
                        "maxLength": 100
                    }
                ],
                "titleTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 370,
                        "yPosition": 125,
                        "tabId": "titleTabId1",
                        "tabLabel": "titleTabLabel1",
                        "name": "titleName1",
                        "fontSize": "size10",
                        "width": 180,
                        "maxLength": 100
                    }
                ],
                "dateTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 370,
                        "yPosition": 150,
                        "tabId": "dateTabId1",
                        "tabLabel": "dateTabLabel1",
                        "name": "dateName1",
                        "fontSize": "size9",
                        "width": 180
                    }
                ],
                "checkboxTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 70,
                        "yPosition": 575,
                        "tabId": "checkboxTabId1",
                        "tabLabel": "checkboxTabLabel1",
                        "name": "checkboxName1",
                        "fontSize": "size9"
                    }
                ],
                "numberTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 70,
                        "yPosition": 600,
                        "tabId": "numberTabId1",
                        "tabLabel": "numberTabLabel1",
                        "name": "numberName1",
                        "fontSize": "size9",
                        "width": 50,
                        "maxLength": 3,
                        "conditionalParentLabel": "checkboxTabLabel1",
                        "conditionalParentValue": "on",
                        "required": False
                    }
                ],
                "listTabs": [
                    {
                        "documentId": 1,
                        "pageNumber": 1,
                        "xPosition": 70,
                        "yPosition": 625,
                        "tabId": "listTabId1",
                        "tabLabel": "listTabLabel1",
                        "name": "listName1",
                        "fontSize": "size9",
                        "width": 120,
                        "listItems": [
                            {
                                "text": "First option",
                                "value": "first"
                            },
                            {
                                "text": "Second option",
                                "value": "second"
                            }
                        ]
                    }
                ],
                "radioGroupTabs": [
                    {
                        "documentId": 1,
                        "groupName": "first_group",
                        "radios": [
                            {
                                "pageNumber": 1,
                                "xPosition": 350,
                                "yPosition": 575,
                                "tabId": "radioTabId1",
                                "tabLabel": "radioTabLabel1",
                                "name": "radioName1",
                                "fontSize": "size9",
                                "width": 120,
                                "value": "first_option"
                            },
                            {
                                "pageNumber": 1,
                                "xPosition": 350,
                                "yPosition": 600,
                                "tabId": "radioTabId2",
                                "tabLabel": "radioTabLabel2",
                                "name": "radioName2",
                                "fontSize": "size9",
                                "width": 120,
                                "value": "second_option"
                            }
                        ]
                    }
                ]
            }
        },
        {
            "recipientId": 2,
            "shouldPauseSigningBefore": False,
            "email": "cesigntest2@gmail.com",
            "name": "Thor Odinson",
            "order": 2,
            "emailSubject": "Thor Odinson, please sign this document",
            "emailBody": "This is the best and the most important document\nfor Signer 2.\n\nBest wishes.",
            "tabs": {
                "signHereTabs": [
                    {
                     "documentId": 1,
                     "pageNumber": 1,
                     "xPosition": 400,
                     "yPosition": 650,
                     "tabId": "signHereTabId199",
                     "tabLabel": "signHereTabLabel99",
                     "name": "signHereName99"
                    }
                ]
            }
        }
    ]
})

REQUEST_WITH_ALL_TABS = cast(dict, _REQUEST_WITH_ALL_TABS)
