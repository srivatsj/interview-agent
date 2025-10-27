"""Tests for CompanyFactory"""

import pytest

from interview_agent.interview_types.system_design.company_factory import CompanyFactory
from interview_agent.interview_types.system_design.tools.amazon_tools import (
    AmazonSystemDesignTools,
)


class TestCompanyFactory:
    """Test CompanyFactory tool creation logic"""

    def test_get_tools_amazon(self):
        """Test getting Amazon tools"""
        tools = CompanyFactory.get_tools("amazon")

        assert isinstance(tools, AmazonSystemDesignTools)
        assert len(tools.get_phases()) == 6

    def test_get_tools_case_insensitive(self):
        """Test factory handles case-insensitive company names"""
        tools1 = CompanyFactory.get_tools("AMAZON")
        tools2 = CompanyFactory.get_tools("Amazon")
        tools3 = CompanyFactory.get_tools("amazon")

        assert isinstance(tools1, AmazonSystemDesignTools)
        assert isinstance(tools2, AmazonSystemDesignTools)
        assert isinstance(tools3, AmazonSystemDesignTools)

    def test_get_tools_invalid_company(self):
        """Test invalid company raises ValueError"""
        with pytest.raises(ValueError, match="Unknown company"):
            CompanyFactory.get_tools("invalid_company")

    def test_get_tools_google_not_implemented(self):
        """Test Google raises NotImplementedError"""
        with pytest.raises(NotImplementedError, match="Tools for google not yet implemented"):
            CompanyFactory.get_tools("google")
