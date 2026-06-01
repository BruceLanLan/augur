# -*- coding: utf-8 -*-
"""
augur.optimizer - Portfolio Optimization (Pure Python Markowitz)

Implements mean-variance optimization for portfolio allocation
using pure Python matrix operations (no numpy/scipy dependency).
Supports matrices up to 10x10.

Architecture:
    - Matrix utilities: transpose, multiply, inverse (Gauss-Jordan), dot product
    - PortfolioOptimizer: Markowitz mean-variance optimization engine
    - Efficient frontier generation with analytical Lagrangian solution
    - Iterative long-only constraint enforcement (asset removal method)

Key Algorithms:
    - Maximum Sharpe ratio: Cov^-1 * (mu - rf) analytical solution
    - Minimum variance at target return: Lagrange multiplier method
    - Long-only enforcement: iteratively remove most-negative-weight asset
      and re-solve until all weights are non-negative (preserves return target)

Error Handling:
    - Singular/near-singular matrices: falls back to equal-weight portfolio
    - Zero-variance assets: regularization epsilon added to diagonal
    - Single-asset portfolios: trivial solution without matrix ops
    - Empty portfolio: returns zero-valued OptimalPortfolio

Usage:
    optimizer = PortfolioOptimizer()
    result = optimizer.optimize({"AAPL": [...], "NVDA": [...]})
    frontier = optimizer.efficient_frontier(returns_data, n_points=20)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ============ Matrix Operations (Pure Python) ============

def matrix_transpose(m: List[List[float]]) -> List[List[float]]:
    """Transpose a matrix."""
    if not m:
        return []
    rows = len(m)
    cols = len(m[0])
    return [[m[i][j] for i in range(rows)] for j in range(cols)]


def matrix_multiply(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
    """Multiply two matrices."""
    rows_a = len(a)
    cols_a = len(a[0]) if a else 0
    cols_b = len(b[0]) if b else 0

    result = [[0.0] * cols_b for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            s = 0.0
            for k in range(cols_a):
                s += a[i][k] * b[k][j]
            result[i][j] = s
    return result


def matrix_inverse(m: List[List[float]]) -> List[List[float]]:
    """Compute inverse of a square matrix using Gauss-Jordan elimination.

    Works for matrices up to 10x10.
    Raises ValueError if matrix is singular.
    """
    n = len(m)
    if n == 0:
        return []
    if n > 10:
        raise ValueError("Matrix too large (max 10x10)")

    # Create augmented matrix [m | I]
    aug = [[0.0] * (2 * n) for _ in range(n)]
    for i in range(n):
        for j in range(n):
            aug[i][j] = m[i][j]
        aug[i][n + i] = 1.0

    # Forward elimination with partial pivoting
    for col in range(n):
        # Find pivot
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row

        if max_val < 1e-12:
            raise ValueError("Matrix is singular or nearly singular")

        # Swap rows
        aug[col], aug[max_row] = aug[max_row], aug[col]

        # Eliminate column
        pivot = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= pivot

        for row in range(n):
            if row != col:
                factor = aug[row][col]
                for j in range(2 * n):
                    aug[row][j] -= factor * aug[col][j]

    # Extract inverse from augmented matrix
    inverse = [[aug[i][n + j] for j in range(n)] for i in range(n)]
    return inverse


def matrix_vector_multiply(m: List[List[float]], v: List[float]) -> List[float]:
    """Multiply matrix by vector."""
    return [sum(m[i][j] * v[j] for j in range(len(v))) for i in range(len(m))]


def vector_dot(a: List[float], b: List[float]) -> float:
    """Dot product of two vectors."""
    return sum(x * y for x, y in zip(a, b))


# ============ Portfolio Optimization ============

@dataclass
class OptimalPortfolio:
    """Result of portfolio optimization."""
    weights: Dict[str, float]  # ticker -> weight
    expected_return: float
    variance: float
    volatility: float
    sharpe_ratio: float

    def to_dict(self) -> Dict:
        return {
            "weights": self.weights,
            "expected_return": round(self.expected_return, 6),
            "variance": round(self.variance, 6),
            "volatility": round(self.volatility, 6),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
        }


@dataclass
class EfficientFrontierPoint:
    """A single point on the efficient frontier."""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class PortfolioOptimizer:
    """Markowitz mean-variance portfolio optimizer (pure Python).

    Implements:
    - Expected return calculation
    - Covariance matrix estimation
    - Minimum variance portfolio
    - Maximum Sharpe ratio portfolio
    - Efficient frontier generation
    """

    def __init__(self):
        pass

    def calculate_returns(self, prices: List[List[float]]) -> List[List[float]]:
        """Calculate periodic returns from price series.

        Args:
            prices: List of price series per asset (each is a list of prices over time)

        Returns:
            List of return series per asset
        """
        returns = []
        for series in prices:
            if len(series) < 2:
                returns.append([])
                continue
            r = [(series[i] - series[i - 1]) / series[i - 1]
                 for i in range(1, len(series)) if series[i - 1] != 0]
            returns.append(r)
        return returns

    def mean_returns(self, returns: List[List[float]]) -> List[float]:
        """Calculate mean return for each asset."""
        means = []
        for r in returns:
            if not r:
                means.append(0.0)
            else:
                means.append(sum(r) / len(r))
        return means

    def covariance_matrix(self, returns: List[List[float]]) -> List[List[float]]:
        """Calculate sample covariance matrix from returns.

        Handles zero-variance assets by adding a small regularization term
        to the diagonal to prevent singular matrices.
        """
        n = len(returns)
        means = self.mean_returns(returns)

        # Find minimum period length
        min_len = min(len(r) for r in returns) if returns else 0
        if min_len < 2:
            return [[0.0] * n for _ in range(n)]

        cov = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                s = 0.0
                for t in range(min_len):
                    s += (returns[i][t] - means[i]) * (returns[j][t] - means[j])
                cov[i][j] = s / (min_len - 1)

        # Regularization: add small epsilon to diagonal for zero-variance assets
        for i in range(n):
            if abs(cov[i][i]) < 1e-12:
                cov[i][i] = 1e-8

        return cov

    def portfolio_return(self, weights: List[float], mean_rets: List[float]) -> float:
        """Calculate expected portfolio return."""
        return vector_dot(weights, mean_rets)

    def portfolio_variance(self, weights: List[float], cov: List[List[float]]) -> float:
        """Calculate portfolio variance."""
        # w^T * Cov * w
        cov_w = matrix_vector_multiply(cov, weights)
        return vector_dot(weights, cov_w)

    def sharpe_ratio(self, expected_return: float, volatility: float, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio."""
        if volatility <= 0:
            return 0.0
        return (expected_return - risk_free_rate) / volatility

    def optimize(
        self,
        returns_data: Dict[str, List[float]],
        risk_free_rate: float = 0.02,
    ) -> OptimalPortfolio:
        """Find the optimal portfolio (maximum Sharpe ratio).

        Args:
            returns_data: Dict of ticker -> list of periodic returns
            risk_free_rate: Annual risk-free rate (default 2%)

        Returns:
            OptimalPortfolio with optimal weights and metrics
        """
        tickers = list(returns_data.keys())
        n = len(tickers)

        if n == 0:
            return OptimalPortfolio(
                weights={}, expected_return=0.0, variance=0.0,
                volatility=0.0, sharpe_ratio=0.0
            )

        if n == 1:
            ticker = tickers[0]
            rets = returns_data[ticker]
            mean_r = sum(rets) / len(rets) if rets else 0.0
            var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1) if len(rets) > 1 else 0.0
            vol = math.sqrt(var)
            sr = self.sharpe_ratio(mean_r, vol, risk_free_rate)
            return OptimalPortfolio(
                weights={ticker: 1.0},
                expected_return=mean_r,
                variance=var,
                volatility=vol,
                sharpe_ratio=sr,
            )

        returns_list = [returns_data[t] for t in tickers]
        mean_rets = self.mean_returns(returns_list)
        cov = self.covariance_matrix(returns_list)

        # Use analytical solution for max Sharpe ratio:
        # w* = Cov^-1 * (mu - rf) / (1^T * Cov^-1 * (mu - rf))
        try:
            cov_inv = matrix_inverse(cov)
        except ValueError:
            # If singular, use equal weights
            w = [1.0 / n] * n
            port_ret = self.portfolio_return(w, mean_rets)
            port_var = self.portfolio_variance(w, cov)
            port_vol = math.sqrt(max(port_var, 0))
            sr = self.sharpe_ratio(port_ret, port_vol, risk_free_rate)
            return OptimalPortfolio(
                weights={tickers[i]: w[i] for i in range(n)},
                expected_return=port_ret,
                variance=port_var,
                volatility=port_vol,
                sharpe_ratio=sr,
            )

        # Excess returns
        excess = [mean_rets[i] - risk_free_rate for i in range(n)]

        # Cov^-1 * excess
        z = matrix_vector_multiply(cov_inv, excess)

        # Normalize weights to sum to 1
        z_sum = sum(z)
        if abs(z_sum) < 1e-12:
            w = [1.0 / n] * n
        else:
            w = [zi / z_sum for zi in z]

        # Handle negative weights by clamping (long-only constraint)
        # If any weight is negative, redistribute
        has_negative = any(wi < 0 for wi in w)
        if has_negative:
            # Simple long-only: set negatives to 0, renormalize
            w = [max(wi, 0.0) for wi in w]
            w_sum = sum(w)
            if w_sum > 0:
                w = [wi / w_sum for wi in w]
            else:
                w = [1.0 / n] * n

        port_ret = self.portfolio_return(w, mean_rets)
        port_var = self.portfolio_variance(w, cov)
        port_vol = math.sqrt(max(port_var, 0))
        sr = self.sharpe_ratio(port_ret, port_vol, risk_free_rate)

        return OptimalPortfolio(
            weights={tickers[i]: round(w[i], 6) for i in range(n)},
            expected_return=port_ret,
            variance=port_var,
            volatility=port_vol,
            sharpe_ratio=sr,
        )

    def efficient_frontier(
        self,
        returns_data: Dict[str, List[float]],
        risk_free_rate: float = 0.02,
        n_points: int = 20,
    ) -> List[EfficientFrontierPoint]:
        """Generate points on the efficient frontier.

        Args:
            returns_data: Dict of ticker -> list of periodic returns
            risk_free_rate: Risk-free rate
            n_points: Number of points to generate

        Returns:
            List of EfficientFrontierPoint objects
        """
        tickers = list(returns_data.keys())
        n = len(tickers)
        if n < 2:
            return []

        returns_list = [returns_data[t] for t in tickers]
        mean_rets = self.mean_returns(returns_list)
        cov = self.covariance_matrix(returns_list)

        min_ret = min(mean_rets)
        max_ret = max(mean_rets)

        if abs(max_ret - min_ret) < 1e-10:
            return []

        points = []
        for i in range(n_points):
            target_ret = min_ret + (max_ret - min_ret) * i / (n_points - 1)

            # Find minimum variance portfolio for target return
            # using a simple grid/iterative approach for small portfolios
            best_w = self._min_var_for_return(
                tickers, mean_rets, cov, target_ret, n
            )

            port_ret = self.portfolio_return(best_w, mean_rets)
            port_var = self.portfolio_variance(best_w, cov)
            port_vol = math.sqrt(max(port_var, 0))
            sr = self.sharpe_ratio(port_ret, port_vol, risk_free_rate)

            points.append(EfficientFrontierPoint(
                expected_return=round(port_ret, 6),
                volatility=round(port_vol, 6),
                sharpe_ratio=round(sr, 4),
                weights={tickers[j]: round(best_w[j], 4) for j in range(n)},
            ))

        return points

    def _min_var_for_return(
        self,
        tickers: List[str],
        mean_rets: List[float],
        cov: List[List[float]],
        target_ret: float,
        n: int,
    ) -> List[float]:
        """Find minimum variance portfolio for a given target return.

        Uses Lagrangian approach for 2 assets, analytical constrained
        optimization via Lagrange multipliers for n > 2.
        Implements iterative removal of negative-weight assets to enforce
        long-only constraint while preserving the return-targeting property.
        """
        if n == 2:
            # Analytical solution for 2 assets
            if abs(mean_rets[0] - mean_rets[1]) < 1e-12:
                return [0.5, 0.5]
            w1 = (target_ret - mean_rets[1]) / (mean_rets[0] - mean_rets[1])
            w1 = max(0.0, min(1.0, w1))
            return [w1, 1.0 - w1]

        # For n > 2, use iterative Lagrangian with asset removal.
        # If a weight is negative, remove that asset and re-solve until all >= 0.
        active_indices = list(range(n))

        for _iteration in range(n):
            k = len(active_indices)
            if k < 2:
                # Only one asset left, give it all weight
                w_full = [0.0] * n
                if active_indices:
                    w_full[active_indices[0]] = 1.0
                return w_full

            # Build sub-matrices for active assets
            sub_mean = [mean_rets[i] for i in active_indices]
            sub_cov = [[cov[i][j] for j in active_indices] for i in active_indices]

            # Clamp target to achievable range for active assets
            sub_min_ret = min(sub_mean)
            sub_max_ret = max(sub_mean)
            clamped_target = max(sub_min_ret, min(sub_max_ret, target_ret))

            try:
                cov_inv = matrix_inverse(sub_cov)
            except ValueError:
                # Singular matrix - use equal weights among active
                w_full = [0.0] * n
                for idx in active_indices:
                    w_full[idx] = 1.0 / k
                return w_full

            ones = [1.0] * k
            mu = sub_mean

            cov_inv_ones = matrix_vector_multiply(cov_inv, ones)
            cov_inv_mu = matrix_vector_multiply(cov_inv, mu)

            A = vector_dot(ones, cov_inv_mu)
            B = vector_dot(mu, cov_inv_mu)
            C = vector_dot(ones, cov_inv_ones)

            denom = B * C - A * A
            if abs(denom) < 1e-12:
                w_full = [0.0] * n
                for idx in active_indices:
                    w_full[idx] = 1.0 / k
                return w_full

            lam = (C * clamped_target - A) / denom
            gam = (B - A * clamped_target) / denom

            w_sub = [lam * cov_inv_mu[i] + gam * cov_inv_ones[i] for i in range(k)]

            # Check for negative weights
            negative_indices = [i for i, wi in enumerate(w_sub) if wi < -1e-10]
            if not negative_indices:
                # All weights non-negative - we are done
                w_full = [0.0] * n
                for idx_local, idx_global in enumerate(active_indices):
                    w_full[idx_global] = max(0.0, w_sub[idx_local])
                # Renormalize to handle floating point
                w_sum = sum(w_full)
                if w_sum > 0:
                    w_full = [wi / w_sum for wi in w_full]
                return w_full

            # Remove the most negative asset and re-solve
            most_negative_local = min(negative_indices, key=lambda i: w_sub[i])
            active_indices = [
                idx for i, idx in enumerate(active_indices)
                if i != most_negative_local
            ]

        # Fallback: equal weight among remaining active
        w_full = [0.0] * n
        if active_indices:
            for idx in active_indices:
                w_full[idx] = 1.0 / len(active_indices)
        else:
            w_full = [1.0 / n] * n
        return w_full
