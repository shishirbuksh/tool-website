from django.urls import path
from apps.tools_api import views

urlpatterns = [
    path("api/remove-background", views.remove_background_view, name="api_remove_background"),
    path("api/remove-watermark", views.remove_watermark_view, name="api_remove_watermark"),
    path("api/convert-to-pdf", views.convert_to_pdf_view, name="api_convert_to_pdf"),
    path("api/crypto-rates", views.crypto_rates_view, name="api_crypto_rates"),
    path("api/fng", views.crypto_fng_view, name="api_crypto_fng"),
    path("api/predict-crypto", views.crypto_predict_view, name="api_predict_crypto"),
    path("api/predict-crypto-async", views.crypto_predict_async_view, name="api_predict_crypto_async"),
    path("api/analyze-crypto-trend-async", views.crypto_analyze_async_view, name="api_analyze_crypto_async"),
    path("api/jobs/<str:job_id>", views.job_status_view, name="api_job_status"),
    path("api/contact", views.contact_view, name="api_contact"),
    path("api/generate-nft", views.generate_nft_view, name="api_generate_nft"),
    path("api/proxy-request", views.proxy_request_view, name="api_proxy_request"),
]
