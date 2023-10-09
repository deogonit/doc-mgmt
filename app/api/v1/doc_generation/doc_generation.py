from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.api.logging_route import LoggingRoute
from app.auth import verify_api_key
from app.base.exception import merge_exception_descriptions
from app.container import Container
from app.doc_generation.exception import (
    FileDoesntExistException,
    FolderAccessForbiddenException,
    MissingVariablesInTemplateException,
    UnsupportedTemplateExtensionException,
)
from app.doc_generation.schema import (
    DocGenMergeRequest,
    DocGenMultipleRequest,
    DocGenMultipleResponse,
    DocGenSingleRequest,
    DocGenSingleResponse,
)
from app.doc_generation.services.convertor import FileConvertorService
from app.file_storage.exception import DynamicS3Exception, NoSuchBucketException
from app.new_relic import TransactionGroupName, track_transaction

DOCGEN_SERVICE_DEPEND = Depends(Provide[Container.doc_gen_service])

router = APIRouter(
    prefix="/doc-generation",
    tags=["doc-generation"],
    route_class=LoggingRoute,
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/single",
    response_model=DocGenSingleResponse,
    responses=merge_exception_descriptions(
        FileDoesntExistException,
        UnsupportedTemplateExtensionException,
        MissingVariablesInTemplateException,
        NoSuchBucketException,
        FolderAccessForbiddenException,
        DynamicS3Exception,
    )
)
@track_transaction(TransactionGroupName.doc_gen)
@inject
async def generate_single_pdf_document(
    doc_gen_schema: DocGenSingleRequest,
    doc_gen_service: FileConvertorService = DOCGEN_SERVICE_DEPEND,
) -> DocGenSingleResponse:
    """
    Endpoint for generating only a single PDF file from a template file. Endpoint supports generating a file from
    docx, pdf, and html templates. All template files and saved files will locate in the main S3 bucket.

    **Algorithm**:
    1. Check that the template file exists in S3 bucket.If a request exists, the app should return it. If not -
    the application will create a new one.
    2. Check that input request exists in Documents table in DynamoDB. If request exists, app should return it. If not -
    application will create a new one.
    3. Check that client passes all required template variables.
    3. Create a new file with substituted values.
    4. Convert a newly created file to a PDF file.
    5. Save created document into the S3 bucket.
    5. Save information about the input request and generated file to the DynamoDB table.
    6. Return the object which contains a path to the document and bucket name.

    For converting files from Docx and HTML to pdf files, the application uses the Gotenberg service.
    For converting files from pdf form to pdf files, the application uses the pypdf library.

    **Args**:
    - **doc_gen_schema**: DocGenSingleRequest object. This object contains information about the template path, template
    variables, and bucket name and optionally client can add the path to the watermark. If you want to generate a file
    from  an HTML template, you can optionally add paths to the header or footer file.
    - **doc_gen_service**: FileConvertorService object. This param will be automatically injected by the
    dependency-injector library.

    **Returns**:
    - **DocGenSingleResponse**: Returns an object with a bucket name and the path to the document in the corresponding
    bucket.

    **Raises**:
    - **FileContentDoesntExistInRegistryException**: Raises an exception, when file content doesn't exist in the file
    registry.
    - **FileDoesntExistException**: Raises an exception, when the template file doesn't exist in the S3 bucket.
    - **FolderAccessForbiddenException**: Raises an exception, when the client want to use a template file from the main
    S3 bucket and not from the directory with the name "templates"
    - **ValueError**: Raises an exception, when the client wants to generate a file from not existing template format.
    - **MissingVariablesInTemplateException**: Raises an exception, when the client passes not correct or not existing
    values of template variables.
    - **UnsupportedTemplateExtensionException**: Raises an exception, when the client wants to generate a file from not
    existing template format.
    """

    doc_path = (await doc_gen_service.generate_documents([doc_gen_schema]))[0].document_path

    return DocGenSingleResponse(
        bucket_name=doc_gen_service.main_bucket_name,
        document_path=doc_path,
    )


@router.post(
    "/multiple/merge",
    response_model=DocGenSingleResponse,
    responses=merge_exception_descriptions(
        FileDoesntExistException,
        MissingVariablesInTemplateException,
        UnsupportedTemplateExtensionException,
        NoSuchBucketException,
        FolderAccessForbiddenException,
        DynamicS3Exception,
    )
)
@track_transaction(TransactionGroupName.doc_gen)
@inject
async def generate_document_based_on_diff_templates(
    doc_multiple_gen_schema: DocGenMultipleRequest,
    doc_gen_service: FileConvertorService = DOCGEN_SERVICE_DEPEND,
) -> DocGenSingleResponse:
    """
    Endpoint for generating a single PDF file which will be based on separate templates (!)
    with different data for each template. Endpoint supports generating files from Docx, pdf, HTML templates.
    All template files and saved files will locate in the main S3 bucket.

    **Algorithm**:
    TBD

    For converting files from Docx and HTML to pdf files, the application uses the Gotenberg service.
    For converting files from pdf form to pdf files, the application uses the pypdf library.

    **Args**:
    - **doc_multiple_gen_schema**: DocGenMultipleRequest object. This object contains a list of DocGenSingleRequest
    items with template path, variables, bucket name, etc.
    - **doc_gen_service**: FileConvertorService object. This param will be automatically injected by the
    dependency-injector library.

    **Returns**:
    - **DocGenSingleResponse**: Returns an object with a bucket name and the path to the document in the corresponding
    bucket.

    **Raises**:
    - **FileContentDoesntExistInRegistryException**: Raises an exception when file content doesn't exist in the
    file registry.
    - **FileDoesntExistException**: Raises an exception when the template file doesn't exist in the S3 bucket.
    - **FolderAccessForbiddenException**: Raises an exception when client wants to use a template file from the
    main S3 bucket and not from the directory with the name "templates"
    - **ValueError**: Raises an exception when the client wants to generate a file from not existing template format.
    - **MissingVariablesInTemplateException**: Raises an exception, when the client pass not correct or not existing
    values of template variables
    - **UnsupportedTemplateExtensionException**: Raises an exception when the client wants to generate a file from not
    existing template format.
    """

    doc_path = await doc_gen_service.generate_documents_and_merge_it(doc_multiple_gen_schema.templates)

    return DocGenSingleResponse(
        bucket_name=doc_gen_service.main_bucket_name,
        document_path=doc_path,
    )


@router.post(
    "/multiple",
    response_model=DocGenMultipleResponse,
    responses=merge_exception_descriptions(
        FileDoesntExistException,
        MissingVariablesInTemplateException,
        UnsupportedTemplateExtensionException,
        NoSuchBucketException,
        FolderAccessForbiddenException,
        DynamicS3Exception,
    )
)
@track_transaction(TransactionGroupName.doc_gen)
@inject
async def generate_multiple_pdf_documents(
    doc_multiple_gen_schema: DocGenMultipleRequest,
    doc_gen_service: FileConvertorService = DOCGEN_SERVICE_DEPEND,
) -> DocGenMultipleResponse:
    """
    Endpoint for generating a list of PDF files from a separate template file. Endpoint supports generating files from
    Docx, pdf, HTML templates. All template files and saved files will locate in the main S3 bucket.

    **Algorithm**:
    1. Check that the template file exists in the S3 bucket. If the file doesn't exist, the application raises an error.
    2. Check that the input request exists in the Documents table in DynamoDB. If a request exists, the app should
    return it. If not - the application will create a new one.
    3. Check that client passes all required template variables to templates.
    4. Create the new files with substituted values.
    5. Convert the newly created files to PDF files.
    6. Save documents into an S3 bucket.
    7. Save information about input requests and generated files into the DynamoDB table.
    8. Merge information with already generated files and files which generated not in this request.
    9. RReturn a list of items that contain a document path and bucket name in the correct ordering.

    For converting files from Docx and HTML to pdf files, the application uses the Gotenberg service.
    For converting files from pdf form to pdf files, the application uses the pypdf library.

    **Args**:
    - **doc_multiple_gen_schema**: DocGenMultipleRequest object. This object contains a list of DocGenSingleRequest
    items with template path, variables, bucket name, etc.
    - **doc_gen_service**: FileConvertorService object. This param will be automatically injected by the
    dependency-injector library.

    **Returns**:
    - **DocGenMultipleResponse**: Returns an object with a bucket name and a list of items with information about the
    document path and input template path. The ordering of response items has the same order which client sends to
    the app.

    **Raises**:
    - **FileContentDoesntExistInRegistryException**: Raises an exception when file content doesn't exist in the
    file registry.
    - **FileDoesntExistException**: Raises an exception when the template file doesn't exist in the S3 bucket.
    - **FolderAccessForbiddenException**: Raises an exception when client wants to use a template file from the
    main S3 bucket and not from the directory with the name "templates"
    - **ValueError**: Raises an exception when the client wants to generate a file from not existing template format.
    - **MissingVariablesInTemplateException**: Raises an exception, when the client pass not correct or not existing
    values of template variables
    - **UnsupportedTemplateExtensionException**: Raises an exception when the client wants to generate a file from not
    existing template format.
    """

    documents = await doc_gen_service.generate_documents(doc_multiple_gen_schema.templates)

    return DocGenMultipleResponse(
        bucket_name=doc_gen_service.main_bucket_name,
        documents=documents,
    )


@router.post(
    "/merge",
    response_model=DocGenSingleResponse,
    responses=merge_exception_descriptions(
        FileDoesntExistException,
        MissingVariablesInTemplateException,
        UnsupportedTemplateExtensionException,
        NoSuchBucketException,
        FolderAccessForbiddenException,
        DynamicS3Exception,
    )
)
@track_transaction(TransactionGroupName.doc_gen)
@inject
async def convert_and_merge_pdf_documents(
    doc_merge_schema: DocGenMergeRequest,
    doc_gen_service: FileConvertorService = DOCGEN_SERVICE_DEPEND,
) -> DocGenSingleResponse:
    """
    Endpoint for generating a single PDF file from a list of templates. Endpoint supports generating files from Docx,
    pdf, and HTML templates. All template files and saved PDFs will locate in the main S3 bucket.

    **Algorithm**:
    1. Check that the template file exists in the S3 bucket. If the file doesn't exist, the application raises an error.
    2. Check that the input request exists in the Documents table in DynamoDB. If a request exists, the app should
    return it. If not - the application will create a new one.
    3. Check that client passes all required template variables to templates.
    3. Create the new files with substituted values.
    4. Convert the newly created files to PDF files and save them in memory
    5. Merge already converted files into one PDF file.
    6. Save the merged PDF document into the S3 bucket.
    5. Save information about the input request and generated file to the DynamoDB table.
    6. Return the object which contains the path to the document and bucket name.

    For converting files from Docx and HTML to pdf files, the application uses the Gotenberg service.
    For converting files from pdf form to pdf files, the application use the pypdf library.

    **Args**:
    - **doc_gen_schema**: DocGenSingleRequest object. This object contains information about template path, template
    variables, bucket name and optionally client can add path to watermark. If you want to generate file from html
    template, you can optionally add paths to header or footer file.
    - **doc_gen_service**: FileConvertorService object. This param will be automatically injected by dependency-injector
    library.

    **Returns**:
    - **DocGenSingleResponse**: Returns an object with a bucket name and the path to the document in the corresponding
    bucket.

    **Raises**:
    - **FileContentDoesntExistInRegistryException**: Raises an exception when file content doesn't exist in the
    file registry.
    - **FileDoesntExistException**: Raises an exception when the template file doesn't exist in the S3 bucket.
    - **FolderAccessForbiddenException**: Raises an exception when client wants to use a template file from the main
    S3 bucket and not from the directory with the name "templates"
    - **ValueError**: Raises an exception when the client wants to generate a file from not existing template format.
    - **MissingVariablesInTemplateException**: Raises an exception, when the client pass not correct or not existing
    values of template variables
    - **UnsupportedTemplateExtensionException**: Raises an exception when the client wants to generate a file from not
    existing template format.
    """

    doc_path = await doc_gen_service.generate_and_merge_documents(doc_merge_schema)

    return DocGenSingleResponse(
        bucket_name=doc_gen_service.main_bucket_name,
        document_path=doc_path,
    )
