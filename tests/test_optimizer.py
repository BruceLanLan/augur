# -*- coding: utf-8 -*-
"""Tests for augur.optimizer - Portfolio Optimization"""

import math
import pytest
from augur.optimizer import (
    PortfolioOptimizer,
    OptimalPortfolio,
    matrix_transpose,
    matrix_multiply,
    matrix_inverse,
    matrix_vector_multiply,
    vector_dot,
)


class TestMatrixOperations:
    def test_transpose(self):
        """Transpose a 2x3 matrix."""
        m = [[1, 2, 3], [4, 5, 6]]
        t = matrix_transpose(m)
        assert t == [[1, 4], [2, 5], [3, 6]]

    def test_transpose_square(self):
        """Transpose a square matrix."""
        m = [[1, 2], [3, 4]]
        t = matrix_transpose(m)
        assert t == [[1, 3], [2, 4]]

    def test_multiply_identity(self):
        """Multiplying by identity returns original."""
        m = [[1, 2], [3, 4]]
        i = [[1, 0], [0, 1]]
        result = matrix_multiply(m, i)
        assert result == [[1, 2], [3, 4]]

    def test_multiply_2x2(self):
        """Multiply two 2x2 matrices."""
        a = [[1, 2], [3, 4]]
        b = [[5, 6], [7, 8]]
        result = matrix_multiply(a, b)
        assert result == [[19, 22], [43, 50]]

    def test_inverse_2x2(self):
        """Inverse of 2x2 matrix."""
        m = [[4, 7], [2, 6]]
        inv = matrix_inverse(m)
        # Verify M * M^-1 = I
        product = matrix_multiply(m, inv)
        assert abs(product[0][0] - 1.0) < 1e-9
        assert abs(product[0][1]) < 1e-9
        assert abs(product[1][0]) < 1e-9
        assert abs(product[1][1] - 1.0) < 1e-9

    def test_inverse_3x3(self):
        """Inverse of 3x3 matrix."""
        m = [[1, 2, 3], [0, 1, 4], [5, 6, 0]]
        inv = matrix_inverse(m)
        product = matrix_multiply(m, inv)
        for i in range(3):
            for j in range(3):
                expected = 1.0 if i == j else 0.0
                assert abs(product[i][j] - expected) < 1e-9

    def test_inverse_singular_raises(self):
        """Singular matrix raises ValueError."""
        m = [[1, 2], [2, 4]]
        with pytest.raises(ValueError):
            matrix_inverse(m)

    def test_vector_dot(self):
        """Dot product of two vectors."""
        a = [1, 2, 3]
        b = [4, 5, 6]
        assert vector_dot(a, b) == 32

    def test_matrix_vector_multiply(self):
        """Matrix-vector multiplication."""
        m = [[1, 2], [3, 4]]
        v = [5, 6]
        result = matrix_vector_multiply(m, v)
        assert result == [17, 39]


class TestPortfolioOptimizer:
    def test_single_asset(self):
        """Single asset portfolio gets weight 1.0."""
        opt = PortfolioOptimizer()
        returns_data = {"AAPL": [0.01, 0.02, -0.01, 0.03, 0.005]}
        result = opt.optimize(returns_data)
        assert isinstance(result, OptimalPortfolio)
        assert result.weights == {"AAPL": 1.0}

    def test_two_assets(self):
        """Two asset portfolio returns valid weights."""
        opt = PortfolioOptimizer()
        returns_data = {
            "AAPL": [0.01, 0.02, -0.01, 0.03, 0.005, 0.015, -0.005, 0.02, 0.01, -0.01],
            "MSFT": [0.005, 0.015, 0.01, -0.005, 0.02, 0.01, 0.005, -0.01, 0.015, 0.025],
        }
        result = opt.optimize(returns_data)
        # Weights should sum to ~1.0
        total = sum(result.weights.values())
        assert abs(total - 1.0) < 0.01
        # All weights >= 0 (long-only)
        for w in result.weights.values():
            assert w >= 0.0

    def test_sharpe_ratio_calculation(self):
        """Sharpe ratio is computed correctly."""
        opt = PortfolioOptimizer()
        sr = opt.sharpe_ratio(0.10, 0.15, 0.02)
        expected = (0.10 - 0.02) / 0.15
        assert abs(sr - expected) < 1e-10

    def test_sharpe_ratio_zero_vol(self):
        """Sharpe ratio is 0 when volatility is 0."""
        opt = PortfolioOptimizer()
        assert opt.sharpe_ratio(0.10, 0.0, 0.02) == 0.0

    def test_empty_returns(self):
        """Empty returns data returns empty portfolio."""
        opt = PortfolioOptimizer()
        result = opt.optimize({})
        assert result.weights == {}
        assert result.expected_return == 0.0

    def test_portfolio_return_calculation(self):
        """Portfolio return is weighted sum of asset returns."""
        opt = PortfolioOptimizer()
        weights = [0.6, 0.4]
        mean_rets = [0.05, 0.03]
        ret = opt.portfolio_return(weights, mean_rets)
        assert abs(ret - 0.042) < 1e-10

    def test_covariance_matrix(self):
        """Covariance matrix is square and symmetric."""
        opt = PortfolioOptimizer()
        returns = [
            [0.01, 0.02, -0.01, 0.03],
            [0.005, 0.015, 0.01, -0.005],
        ]
        cov = opt.covariance_matrix(returns)
        assert len(cov) == 2
        assert len(cov[0]) == 2
        # Symmetric
        assert abs(cov[0][1] - cov[1][0]) < 1e-12

    def test_efficient_frontier(self):
        """Efficient frontier returns multiple points."""
        opt = PortfolioOptimizer()
        returns_data = {
            "A": [0.01, 0.02, -0.01, 0.03, 0.005, 0.015, -0.005, 0.02, 0.01, -0.01],
            "B": [0.005, 0.015, 0.01, -0.005, 0.02, 0.01, 0.005, -0.01, 0.015, 0.025],
        }
        points = opt.efficient_frontier(returns_data, n_points=5)
        assert len(points) == 5
        # Each point should have volatility >= 0
        for p in points:
            assert p.volatility >= 0

    def test_optimize_to_dict(self):
        """OptimalPortfolio.to_dict() serializes correctly."""
        opt = PortfolioOptimizer()
        returns_data = {"X": [0.01, 0.02, -0.01, 0.03, 0.005]}
        result = opt.optimize(returns_data)
        d = result.to_dict()
        assert "weights" in d
        assert "expected_return" in d
        assert "volatility" in d
        assert "sharpe_ratio" in d
