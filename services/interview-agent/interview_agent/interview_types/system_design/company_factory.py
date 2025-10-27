"""Factory for creating company-specific system design tools."""

import logging

from .providers import AmazonSystemDesignTools

logger = logging.getLogger(__name__)


class CompanyFactory:
    """Factory for creating company-specific design tools."""

    @staticmethod
    def get_tools(company: str):
        """Get company-specific system design tools.

        Args:
            company: Company name (amazon, google, apple, etc.)

        Returns:
            Company-specific tools instance (e.g., AmazonSystemDesignTools)

        Raises:
            ValueError: If company is not supported
            NotImplementedError: If company tools are not yet implemented
        """
        company_lower = company.lower()
        logger.info(f"Loading tools for company: {company_lower}")

        if company_lower == "amazon":
            return AmazonSystemDesignTools()
        elif company_lower == "google":
            raise NotImplementedError(f"Tools for {company_lower} not yet implemented")
        else:
            raise ValueError(f"Unknown company: {company_lower}")
