"""
AnchorGenerator - Phase 14.2: Metadata Extraction

Extracts GPS, dependency, risk, temporal, and safety metadata.
"""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from cerberus.logging_config import logger
from cerberus.anchoring.schema import (
    AnchorMetadata,
    GPSLocation,
    DependencyInfo,
    RiskInfo,
    RiskLevel,
    TemporalInfo,
    SafetyInfo,
    GuardStatus,
)


class AnchorGenerator:
    """
    Phase 14.2: Generate context anchors from index and git metadata.

    Integrations:
    - Phase 5: Symbolic intelligence (dependencies)
    - Phase 13.2: Stability scoring (risk)
    - Git: Blame for temporal context
    """

    def __init__(self, store=None):
        """
        Initialize anchor generator.

        Args:
            store: SQLiteIndexStore instance (optional)
        """
        self.store = store
        logger.debug("AnchorGenerator initialized")

    def generate_anchor(
        self,
        file_path: str,
        symbol_name: str,
        include_dependencies: bool = True,
        include_risk: bool = True,
        include_temporal: bool = True,
        include_safety: bool = True,
    ) -> Optional[AnchorMetadata]:
        """
        Generate complete anchor metadata for a symbol.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            include_dependencies: Include dependency context
            include_risk: Include risk/stability info
            include_temporal: Include temporal context
            include_safety: Include safety context

        Returns:
            AnchorMetadata or None if symbol not found
        """
        try:
            # 1. GPS Location (required)
            gps = self._extract_gps(file_path, symbol_name)
            if not gps:
                logger.warning(f"Could not extract GPS for {symbol_name} in {file_path}")
                return None

            # 2. Dependencies (optional)
            dependencies = []
            if include_dependencies:
                dependencies = self._extract_dependencies(file_path, symbol_name)

            # 3. Risk Info (optional)
            risk = None
            if include_risk:
                risk = self._extract_risk_info(file_path, symbol_name)

            # 4. Temporal Info (optional)
            temporal = None
            if include_temporal:
                temporal = self._extract_temporal_info(file_path, gps.lines["start"])

            # 5. Safety Info (optional)
            safety = None
            if include_safety:
                safety = self._extract_safety_info(file_path, symbol_name, risk)

            return AnchorMetadata(
                gps=gps,
                dependencies=dependencies,
                risk=risk,
                temporal=temporal,
                safety=safety,
            )

        except Exception as e:
            logger.error(f"Failed to generate anchor: {e}")
            return None

    def _extract_gps(self, file_path: str, symbol_name: str) -> Optional[GPSLocation]:
        """
        Extract GPS location metadata.

        Args:
            file_path: Path to file
            symbol_name: Symbol name

        Returns:
            GPSLocation or None
        """
        try:
            # Phase 14.2: Use index to find symbol location
            if self.store:
                symbols = self.store.find_symbol_by_name(symbol_name, file_path=file_path)
                if symbols:
                    symbol = symbols[0]
                    return GPSLocation(
                        file=file_path,
                        symbol=symbol_name,
                        lines={"start": symbol.start_line, "end": symbol.end_line},
                        symbol_type=symbol.type,
                        parent_class=symbol.parent_class,
                    )

            # Fallback: Create basic GPS without line info
            return GPSLocation(
                file=file_path,
                symbol=symbol_name,
                lines={"start": 0, "end": 0},
            )

        except Exception as e:
            logger.debug(f"GPS extraction failed: {e}")
            return None

    def _extract_dependencies(
        self,
        file_path: str,
        symbol_name: str,
        max_deps: int = 10
    ) -> List[DependencyInfo]:
        """
        Extract dependency context with confidence scores.

        Phase 14.2: Integrates with Phase 5 symbolic intelligence.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            max_deps: Maximum dependencies to return

        Returns:
            List of DependencyInfo
        """
        dependencies = []

        try:
            # Phase 5 integration: Query dependencies
            if self.store:
                # Get calls made by this symbol
                calls = self.store.get_symbol_dependencies(
                    file_path=file_path,
                    symbol_name=symbol_name
                )

                for call in calls[:max_deps]:
                    dependencies.append(DependencyInfo(
                        name=call.get("callee", "unknown"),
                        confidence=call.get("confidence", 0.8),
                        type="call",
                        file=call.get("callee_file"),
                        line=call.get("line"),
                    ))

        except Exception as e:
            logger.debug(f"Dependency extraction failed: {e}")

        return dependencies

    def _extract_risk_info(
        self,
        file_path: str,
        symbol_name: str
    ) -> Optional[RiskInfo]:
        """
        Extract risk and stability metadata.

        Phase 14.2: Integrates with Phase 13.2 stability scoring.

        Args:
            file_path: Path to file
            symbol_name: Symbol name

        Returns:
            RiskInfo or None
        """
        try:
            # Phase 13.2 integration: Query stability metrics
            # For now, use heuristic-based risk assessment
            # TODO: Full integration with Phase 13.2 stability scoring

            factors = {}
            score = 0.0

            # Check git churn (simplified)
            churn = self._get_file_churn(file_path)
            if churn is not None:
                factors["churn_per_week"] = churn
                score += min(churn / 2.0, 0.4)  # Cap at 0.4

            # Check test coverage (simplified)
            coverage = self._estimate_test_coverage(file_path)
            if coverage is not None:
                factors["test_coverage"] = coverage
                score += (1.0 - coverage) * 0.3  # Inverse coverage contributes

            # Determine risk level
            if score < 0.3:
                level = RiskLevel.SAFE
            elif score < 0.7:
                level = RiskLevel.MEDIUM
            else:
                level = RiskLevel.HIGH

            return RiskInfo(
                level=level,
                score=score,
                factors=factors,
            )

        except Exception as e:
            logger.debug(f"Risk extraction failed: {e}")
            return None

    def _extract_temporal_info(
        self,
        file_path: str,
        line_number: int
    ) -> Optional[TemporalInfo]:
        """
        Extract temporal context from git blame.

        Args:
            file_path: Path to file
            line_number: Line number to blame

        Returns:
            TemporalInfo or None
        """
        try:
            # Use git blame to get last modification
            result = subprocess.run(
                ["git", "blame", "-L", f"{line_number},{line_number}", "--porcelain", file_path],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                author = None
                timestamp = None

                for line in lines:
                    if line.startswith("author "):
                        author = line.split("author ", 1)[1]
                    elif line.startswith("author-time "):
                        timestamp_unix = int(line.split("author-time ", 1)[1])
                        timestamp = datetime.fromtimestamp(timestamp_unix).isoformat()

                if timestamp:
                    # Calculate days since last edit
                    timestamp_dt = datetime.fromisoformat(timestamp)
                    days_since = (datetime.now() - timestamp_dt).days

                    return TemporalInfo(
                        last_modified=timestamp,
                        last_modified_by=author,
                        days_since_last_edit=days_since,
                    )

        except Exception as e:
            logger.debug(f"Temporal extraction failed: {e}")

        return None

    def _extract_safety_info(
        self,
        file_path: str,
        symbol_name: str,
        risk: Optional[RiskInfo]
    ) -> Optional[SafetyInfo]:
        """
        Extract safety system integration status.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            risk: Risk info (for Symbol Guard status)

        Returns:
            SafetyInfo or None
        """
        try:
            # Symbol Guard status based on risk level
            if risk:
                if risk.level == RiskLevel.HIGH:
                    guard_status = GuardStatus.BLOCK
                elif risk.level == RiskLevel.MEDIUM:
                    guard_status = GuardStatus.WARN
                else:
                    guard_status = GuardStatus.ALLOW
            else:
                guard_status = GuardStatus.ALLOW

            # Check if verifiable (has tests)
            verifiable = self._has_tests(file_path)

            # Undo is always available in Phase 12.5+
            undo_available = True

            # Check if recently undone (would need undo ledger integration)
            recent_undo = False

            return SafetyInfo(
                symbol_guard=guard_status,
                verifiable=verifiable,
                undo_available=undo_available,
                recent_undo=recent_undo,
            )

        except Exception as e:
            logger.debug(f"Safety extraction failed: {e}")
            return None

    def _get_file_churn(self, file_path: str) -> Optional[float]:
        """
        Get git churn (edits per week) for file.

        Args:
            file_path: Path to file

        Returns:
            Churn rate or None
        """
        try:
            # Get commits in last 90 days
            result = subprocess.run(
                ["git", "log", "--since=90 days ago", "--oneline", "--", file_path],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode == 0:
                commit_count = len(result.stdout.strip().split('\n'))
                if commit_count > 0:
                    # Convert to per-week rate (90 days ~= 13 weeks)
                    return commit_count / 13.0

        except Exception as e:
            logger.debug(f"Churn calculation failed: {e}")

        return None

    def _estimate_test_coverage(self, file_path: str) -> Optional[float]:
        """
        Estimate test coverage for file.

        Args:
            file_path: Path to file

        Returns:
            Coverage estimate (0.0-1.0) or None
        """
        try:
            # Simple heuristic: check if test file exists
            path = Path(file_path)
            test_patterns = [
                f"test_{path.stem}.py",
                f"{path.stem}_test.py",
                f"tests/test_{path.stem}.py",
                f"test/test_{path.stem}.py",
            ]

            for pattern in test_patterns:
                test_path = path.parent / pattern
                if test_path.exists():
                    # Assume decent coverage if test file exists
                    return 0.75

            # No test file found
            return 0.0

        except Exception as e:
            logger.debug(f"Coverage estimation failed: {e}")
            return None

    def _has_tests(self, file_path: str) -> bool:
        """
        Check if file has associated tests.

        Args:
            file_path: Path to file

        Returns:
            True if tests exist
        """
        coverage = self._estimate_test_coverage(file_path)
        return coverage is not None and coverage > 0.0

    def generate_anchor_for_mutation(
        self,
        file_path: str,
        symbol_name: str,
        operation: str,
    ) -> Optional[AnchorMetadata]:
        """
        Generate anchor for mutation operation.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            operation: Operation type (edit, delete, insert)

        Returns:
            AnchorMetadata with mutation context
        """
        # Generate full anchor
        return self.generate_anchor(
            file_path=file_path,
            symbol_name=symbol_name,
            include_dependencies=True,
            include_risk=True,
            include_temporal=False,  # Skip temporal for mutations
            include_safety=True,
        )

    def generate_lightweight_anchor(
        self,
        file_path: str,
        symbol_name: str,
    ) -> Optional[AnchorMetadata]:
        """
        Generate lightweight anchor (GPS + safety only).

        Phase 14.2: For high-frequency operations where full context
        would add too much overhead.

        Args:
            file_path: Path to file
            symbol_name: Symbol name

        Returns:
            Lightweight AnchorMetadata
        """
        return self.generate_anchor(
            file_path=file_path,
            symbol_name=symbol_name,
            include_dependencies=False,
            include_risk=False,
            include_temporal=False,
            include_safety=True,
        )
