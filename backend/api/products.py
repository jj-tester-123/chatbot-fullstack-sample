"""
상품 관련 API 라우터
- GET /products: 상품 목록 조회
- GET /products/{id}: 상품 상세 조회
"""
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from db.repository import (
    get_all_products,
    get_product_by_id,
    get_product_reviews,
    get_product_qnas,
)

router = APIRouter()


class Product(BaseModel):
    """상품 기본 정보"""
    id: int
    name: str
    image_url: str
    price: int
    category: str
    description: str


class ProductText(BaseModel):
    """상품 텍스트 (설명/리뷰/Q&A)"""
    id: int
    product_id: int
    type: str  # description, review, qna
    content: str


class Review(BaseModel):
    """주문 리뷰"""
    id: int
    product_id: int
    user_name: str | None = None
    review_text: str
    rating: int | None = None
    created_at: str


class Qna(BaseModel):
    """상품 Q&A"""
    id: int
    product_id: int
    question: str
    answer: str
    created_at: str


class ProductDetail(BaseModel):
    """상품 상세 정보 (기본 정보 + 리뷰/Q&A)"""
    product: Product
    reviews: List[Review]
    qnas: List[Qna]


@router.get("", response_model=List[Product])
async def list_products():
    """
    상품 목록 조회
    - 모든 상품의 기본 정보를 반환합니다.
    """
    products = get_all_products()
    return products


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product_detail(product_id: int):
    """
    상품 상세 조회
    - 상품 기본 정보 + 관련 텍스트(설명/리뷰/Q&A) 반환
    """
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    reviews = get_product_reviews(product_id)
    qnas = get_product_qnas(product_id)

    return ProductDetail(
        product=product,
        reviews=reviews,
        qnas=qnas,
    )
