import io
import re
import os.path
import uuid
from PIL import Image

import boto3
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from django.conf import settings

S3_CLIENT = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION_NAME
        )


def generate_s3_presigned_url(file_name, file_type):
    extension = os.path.splitext(file_name)[1]
    temp_file_name = f'{uuid.uuid4()}{extension}'
    s3_file_path = f'temp/{temp_file_name}'

    try:
        presigned_url = S3_CLIENT.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': settings.AWS_S3_BUCKET_NAME,
                'Key': s3_file_path,
                'ContentType': file_type,
            },
            ExpiresIn=600
        )

        return {'presigned_url': presigned_url, 's3_key': s3_file_path}

    except ClientError as e:
        print('S3 Presigned URL 생성 중 에러 발생: ', e)


def resize_image_and_upload_to_s3(s3_key):
    width = 800
    height = 600

    try:
        # s3에서 원본 이미지 다운로드 (메모리 버퍼로)
        obj = S3_CLIENT.get_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=s3_key)
        image_data = io.BytesIO(obj['Body'].read())
        image = Image.open(image_data)

        # 이미지 리사이징
        resized_image = image.copy()
        resized_image.thumbnail((width, height), Image.LANCZOS)

        # 리사이즈한 이미지를 메모리 버퍼에 저장
        buffer = io.BytesIO()
        file_extension = image.format
        resized_image.save(buffer, format=file_extension)
        buffer.seek(0)

        # 기존 파일명과 같은 이름으로 s3 resized/ 경로에 저장
        original_filename = os.path.basename(s3_key)
        new_s3_file_path = f'resized/{original_filename}'

        # 리사이징된 이미지를 s3에 업로드
        S3_CLIENT.upload_fileobj(
            buffer,
            settings.AWS_S3_BUCKET_NAME,
            new_s3_file_path,
            ExtraArgs={'ContentType': obj['ContentType']})

        image_url = f'{settings.AWS_CLOUDFRONT_DOMAIN}/{new_s3_file_path}'

        return image_url

    except Exception as e:
        print('이미지 리사이징 및 S3 업로드 중 에러 발생:', e)
        return None


def extract_image_keys_from_content(content):
    parser = BeautifulSoup(content, 'html.parser')
    image_tags = parser.findAll('img')
    image_keys = set()
    cloudfront_domain_prefix = f'{settings.AWS_CLOUDFRONT_DOMAIN}/'

    for img_tag in image_tags:
        src = img_tag.get('src')

        if src and src.startswith(cloudfront_domain_prefix):
            key = src.replace(cloudfront_domain_prefix, '')
            image_keys.add(key)
    print(f'BeautifulSoup으로 추출된 이미지 키: {image_keys}')

    return image_keys



def delete_unused_images(old_content, new_content):
    try:
        old_image_keys = extract_image_keys_from_content(old_content)
        new_image_keys = extract_image_keys_from_content(new_content)

        # 기존 이미지 키 집합에서 새로운 이미지 키 집합을 뺌으로써 삭제 대상 찾기
        images_to_delete = old_image_keys - new_image_keys

        if not images_to_delete:
            print('삭제할 이미지가 없습니다.')
            return

        print(f'삭제할 이미지 키: {images_to_delete}')

        for key in images_to_delete:
            # s3에서 원본 이미지와 리사이즈된 이미지 모두 삭제
            resized_key = key
            original_key = key.replace('resized/', 'content/', 1)

            # 삭제 대상 키들을 리스트에 추가
            keys_to_delete_on_s3 = [resized_key]

            # 원본 키가 'resized/' 키와 다르다면 삭제 리스트에 추가
            if resized_key != original_key:
                keys_to_delete_on_s3.append(original_key)

            for s3_key in keys_to_delete_on_s3:
                try:
                    S3_CLIENT.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=s3_key)
                    print(f's3에서 이미지 삭제 성공: {s3_key}')
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        print(f's3에서 해당 이미지 키를 찾을 수 없습니다: {s3_key}')
                    else:
                        print(f's3에서 이미지 삭제 중 ClientError 발생: {e} - {s3_key}')

    except Exception as e:
        print('이미지 키 추출 또는 S3 이미지 삭제 중 에러 발생:', str(e))


def move_temp_images_to_final_location(content):
    image_keys = extract_image_keys_from_content(content)
    final_content = content

    for key in image_keys:
        if key.startswith('resized/'):
            filename = os.path.basename(key)
            temp_key = f'temp/{filename}'
            final_key = f'content/{filename}'

            try:
                # temp/ 이미지를 content/ 폴더로 복사
                S3_CLIENT.copy_object(
                    Bucket=settings.AWS_S3_BUCKET_NAME,
                    CopySource={'Bucket': settings.AWS_S3_BUCKET_NAME, 'Key': temp_key},
                    Key=final_key,
                )

                # temp/ 폴더에 있는 임시 파일 삭제
                S3_CLIENT.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=temp_key)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    print(f"이미 파일이 없거나 옮겨졌습니다: {temp_key}")
                else:
                    print(f"이미지 폴더 이동 중 ClientError 발생: {e} - {temp_key}")
            except Exception as e:
                print(f'이미지 폴더 이동 중 에러 발생: {e}')

    return final_content
