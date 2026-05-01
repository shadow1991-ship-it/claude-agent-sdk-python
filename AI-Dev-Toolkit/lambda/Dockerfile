# Sentinel Guard — AWS Lambda Container Image
# Base: public.ecr.aws/lambda/provided:al2
# sha256:9301f689176ec540568d95096d958295b8c2ef9fae088e1586274f5c0021a288

FROM public.ecr.aws/lambda/python:3.11

# نسخ الـ handler
COPY scanner_handler.py ${LAMBDA_TASK_ROOT}/

# تثبيت التبعيات
RUN pip install --no-cache-dir \
    httpx>=0.27 \
    openai>=1.0 \
    fastapi>=0.111 \
    mangum>=0.17 \
    pydantic>=2.0

# Lambda handler entry point
CMD ["scanner_handler.handler"]
