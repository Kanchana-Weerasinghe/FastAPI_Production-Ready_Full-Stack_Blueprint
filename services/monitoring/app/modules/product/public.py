"""
PUBLIC API of the product module: the ONLY file other modules of this service may import from.

Re-exports only, no logic. Another module that needs product imports `ProductUseCases`
from here, never from application/ or infrastructure/. Other SERVICES never import this code: they
call `/v1/product` over HTTP.
"""

from app.modules.product.application.use_cases import CreateProductCommand, ProductUseCases, UpdateProductCommand
from app.modules.product.domain.entities import Product
from app.modules.product.domain.value_objects import ProductStatus

__all__ = ["CreateProductCommand", "UpdateProductCommand", "Product", "ProductStatus", "ProductUseCases"]
