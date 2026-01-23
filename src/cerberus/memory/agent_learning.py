"""
PHASE 10: AGENT SELF-LEARNING

Agent detects success/failure patterns and proposes memories proactively.

Components:
- Phase 10A: Detection patterns (success, failure, project, approach)
- Phase 10B: Proposal refinement (rule-based PRIMARY, LLM optional)

Integration: Feeds into Phase 3's existing proposal engine
Target: 50%+ approval rate
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class AgentObservation:
    """Single observation from agent's actions."""
    observation_type: str  # "success", "failure", "pattern", "reinforcement"
    action_taken: str  # What agent did
    user_response: str  # User's reaction (approval, rejection, correction)
    context: Dict[str, Any]  # File, function, tool used, etc.
    confidence: float
    timestamp: datetime


@dataclass
class AgentProposal:
    """Agent-generated memory proposal."""
    id: str
    category: str  # "preference", "rule", "pattern", "correction"
    scope: str  # "universal", "language:X", "project:Y"
    content: str  # The rule (terse, imperative)
    evidence: List[str]  # Supporting observations (terse)
    confidence: float
    priority: int


# ============================================================================
# Helper Functions
# ============================================================================

def _infer_scope(observations: List[AgentObservation]) -> str:
    """
    Infer scope from observation context.
    If all observations from same project → project scope
    If all observations same language → language scope
    Otherwise → universal
    """
    projects = set()
    languages = set()

    for obs in observations:
        ctx = obs.context
        if "project" in ctx:
            projects.add(ctx["project"])
        if "language" in ctx:
            languages.add(ctx["language"])
        # Infer from file extension
        if "file" in ctx:
            ext = Path(ctx["file"]).suffix
            lang_map = {".py": "python", ".go": "go", ".ts": "typescript", ".js": "javascript"}
            if ext in lang_map:
                languages.add(lang_map[ext])

    if len(projects) == 1:
        return f"project:{list(projects)[0]}"
    if len(languages) == 1:
        return f"language:{list(languages)[0]}"
    return "universal"


def _extract_rule(action: str, observations: List[AgentObservation]) -> str:
    """
    Extract a concise rule from action and observations.
    """
    action_lower = action.lower()

    if "split" in action_lower:
        return "Plan file splits before writing (200-line limit)"
    if "test" in action_lower and "first" in action_lower:
        return "Write tests before implementation"
    if "summary" in action_lower or "terse" in action_lower:
        return "Keep summaries 2-3 sentences max"
    if "plan" in action_lower or "design" in action_lower:
        return "Create plan/design before implementation"

    # Fallback: use action directly
    return f"Continue: {action[:50]}"


def _extract_anti_pattern(action: str) -> str:
    """
    Extract what NOT to do from failed action.
    """
    action_lower = action.lower()

    if "verbose" in action_lower or "long" in action_lower:
        return "Verbose explanations"
    if "200" in action or "line" in action_lower:
        return "Writing files >200 lines without splitting"
    if "wait" in action_lower or "delay" in action_lower:
        return "Waiting for confirmation on obvious fixes"

    # Fallback
    return action[:50]


def _extract_praised_approach(obs: AgentObservation) -> str:
    """
    Extract the approach that was praised.
    """
    action = obs.action_taken.lower()
    response = obs.user_response.lower()

    # TDD detection
    if "test" in action and ("tdd" in response or "first" in action):
        return "Write tests before implementation (TDD)"

    # Planning detection
    if "plan" in action or "design" in action:
        return "Create design docs before implementation"

    # Splitting detection
    if "split" in action:
        return "Split large files before they exceed limits"

    # Fallback: use action
    return f"Continue approach: {obs.action_taken[:40]}"


# ============================================================================
# Detection Patterns (Phase 10A)
# ============================================================================

def detect_success_pattern(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    """
    Pattern 1: Success Reinforcement
    Trigger: Action repeated 3+ times, user approved all
    """
    # Group by action type
    by_action = {}
    for obs in observations:
        action = obs.action_taken
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(obs)

    # Find repeated successful actions
    for action, obs_list in by_action.items():
        if len(obs_list) >= 3:
            # Check all approved
            approvals = [
                o for o in obs_list
                if "approved" in o.user_response.lower() or
                   "good" in o.user_response.lower() or
                   "perfect" in o.user_response.lower()
            ]

            if len(approvals) == len(obs_list):
                # All approved → propose rule
                return AgentProposal(
                    id=f"agent-{uuid.uuid4().hex[:8]}",
                    category="rule",
                    scope=_infer_scope(obs_list),
                    content=_extract_rule(action, obs_list),
                    evidence=[f"{o.action_taken} → approved" for o in approvals[:3]],
                    confidence=min(len(approvals) / 10.0, 1.0),
                    priority=1
                )

    return None


def detect_failure_pattern(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    """
    Pattern 2: Failure Avoidance
    Trigger: Action caused correction 2+ times
    """
    # Group by action type
    by_action = {}
    for obs in observations:
        if obs.observation_type == "failure":
            action = obs.action_taken
            if action not in by_action:
                by_action[action] = []
            by_action[action].append(obs)

    # Find repeated failures
    for action, obs_list in by_action.items():
        if len(obs_list) >= 2:
            # Extract what NOT to do
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="correction",
                scope=_infer_scope(obs_list),
                content=f"Avoid: {_extract_anti_pattern(action)}",
                evidence=[f"{o.action_taken} → {o.user_response}" for o in obs_list[:3]],
                confidence=min(len(obs_list) / 5.0, 1.0),
                priority=2
            )

    return None


def detect_project_pattern(
    observations: List[AgentObservation],
    codebase_analysis: Dict
) -> Optional[AgentProposal]:
    """
    Pattern 3: Project Inference
    Trigger: Consistent pattern in codebase, agent follows it 3+ times
    """
    # Analyze codebase patterns
    patterns = codebase_analysis.get("patterns", {})

    # Check if agent followed pattern consistently
    for pattern_name, pattern_data in patterns.items():
        matches = [
            o for o in observations
            if pattern_name in o.action_taken
        ]

        if len(matches) >= 3:
            # Agent consistently follows pattern → propose as rule
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="pattern",
                scope=f"project:{codebase_analysis['project']}",
                content=f"Project pattern: {pattern_data['description']}",
                evidence=[f"applied in {o.context.get('file', 'unknown')}" for o in matches[:3]],
                confidence=0.6,
                priority=3
            )

    return None


def detect_approach_reinforcement(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    """
    Pattern 4: Approach Reinforcement
    Trigger: Specific approach praised explicitly
    """
    # Look for explicit praise
    praise_keywords = ["perfect", "exactly", "great", "excellent", "correct"]

    for obs in observations:
        if any(kw in obs.user_response.lower() for kw in praise_keywords):
            # Extract what was praised
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="preference",
                scope=_infer_scope([obs]),
                content=_extract_praised_approach(obs),
                evidence=[f"{obs.action_taken} → '{obs.user_response}'"],
                confidence=0.9,  # Explicit praise = high confidence
                priority=1
            )

    return None


# ============================================================================
# Observation Collection
# ============================================================================

class ObservationCollector:
    """
    Collects observations during session.
    """

    def __init__(self):
        self.observations: List[AgentObservation] = []

    def record(
        self,
        action: str,
        user_response: str,
        context: Dict,
        obs_type: Optional[str] = None
    ):
        """
        Record single observation.
        Called after each user response.
        """
        # Classify observation type if not provided
        if obs_type is None:
            if any(kw in user_response.lower() for kw in ["don't", "never", "stop"]):
                obs_type = "failure"
            elif any(kw in user_response.lower() for kw in ["perfect", "good", "correct"]):
                obs_type = "success"
            else:
                obs_type = "neutral"

        obs = AgentObservation(
            observation_type=obs_type,
            action_taken=action,
            user_response=user_response,
            context=context,
            confidence=self._calculate_confidence(user_response),
            timestamp=datetime.now()
        )

        self.observations.append(obs)

    def _calculate_confidence(self, response: str) -> float:
        """
        Calculate confidence from user response.
        Explicit praise = 0.9
        Implicit approval = 0.7
        Neutral = 0.5
        Correction = 0.3
        """
        response_lower = response.lower()

        if any(kw in response_lower for kw in ["perfect", "exactly", "excellent"]):
            return 0.9
        if any(kw in response_lower for kw in ["good", "correct", "right"]):
            return 0.7
        if any(kw in response_lower for kw in ["don't", "never", "stop"]):
            return 0.3

        return 0.5


# ============================================================================
# Codebase Analysis
# ============================================================================

class CodebaseAnalyzer:
    """
    Analyzes codebase for patterns.
    Detects common coding patterns from file analysis.
    """

    def analyze(self, project: str, project_path: Optional[Path] = None) -> Dict:
        """
        Analyze codebase for patterns.
        """
        if project_path is None:
            project_path = Path.cwd()

        patterns = {}

        # Pattern 1: Error handling style
        error_patterns = self._detect_error_handling(project_path)
        if error_patterns:
            patterns["error_handling"] = error_patterns

        # Pattern 2: Test framework usage
        test_patterns = self._detect_test_patterns(project_path)
        if test_patterns:
            patterns["testing"] = test_patterns

        # Pattern 3: Import organization
        import_patterns = self._detect_import_patterns(project_path)
        if import_patterns:
            patterns["imports"] = import_patterns

        return {"project": project, "patterns": patterns}

    def _detect_error_handling(self, path: Path) -> Optional[Dict]:
        """Detect error handling patterns in codebase."""
        patterns = []

        # Go error handling
        go_files = list(path.rglob("*.go"))
        if go_files:
            err_nil_count = 0
            logger_count = 0
            for f in go_files[:20]:  # Sample 20 files max
                try:
                    content = f.read_text()
                    err_nil_count += content.count("if err != nil")
                    logger_count += content.count("logger.Error") + content.count("log.Error")
                except:
                    pass

            if err_nil_count > 5 and logger_count > 3:
                return {
                    "description": "Log errors before returning (Go style)",
                    "confidence": min(logger_count / err_nil_count, 1.0)
                }

        # Python exception handling
        py_files = list(path.rglob("*.py"))
        if py_files:
            try_count = 0
            logging_count = 0
            for f in py_files[:20]:
                try:
                    content = f.read_text()
                    try_count += content.count("try:")
                    logging_count += content.count("logging.") + content.count("logger.")
                except:
                    pass

            if try_count > 5 and logging_count > 3:
                return {
                    "description": "Use logging in exception handlers",
                    "confidence": min(logging_count / max(try_count, 1), 1.0)
                }

        return None

    def _detect_test_patterns(self, path: Path) -> Optional[Dict]:
        """Detect testing patterns in codebase."""
        # Go: testify vs standard
        go_test_files = list(path.rglob("*_test.go"))
        if go_test_files:
            testify_count = 0
            for f in go_test_files[:10]:
                try:
                    content = f.read_text()
                    if "testify" in content or "suite.Suite" in content:
                        testify_count += 1
                except:
                    pass

            if testify_count >= 3:
                return {
                    "description": "Use testify.Suite for test organization",
                    "confidence": testify_count / len(go_test_files[:10])
                }

        # Python: pytest vs unittest
        py_test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if py_test_files:
            pytest_count = 0
            for f in py_test_files[:10]:
                try:
                    content = f.read_text()
                    if "import pytest" in content or "@pytest" in content:
                        pytest_count += 1
                except:
                    pass

            if pytest_count >= 3:
                return {
                    "description": "Use pytest fixtures and parametrize",
                    "confidence": pytest_count / len(py_test_files[:10])
                }

        return None

    def _detect_import_patterns(self, path: Path) -> Optional[Dict]:
        """Detect import organization patterns."""
        py_files = list(path.rglob("*.py"))
        if py_files:
            sorted_imports = 0
            for f in py_files[:10]:
                try:
                    content = f.read_text()
                    # Check for isort-style grouping (stdlib, third-party, local)
                    if "from __future__" in content or "\n\nimport " in content:
                        sorted_imports += 1
                except:
                    pass

            if sorted_imports >= 5:
                return {
                    "description": "Group imports: stdlib, third-party, local",
                    "confidence": sorted_imports / len(py_files[:10])
                }

        return None


# ============================================================================
# Proposal Refinement (Phase 10B)
# ============================================================================

class ProposalRefiner:
    """
    Refine agent proposals into canonical form.

    PRIMARY: Rule-based refinement (no dependencies, instant)
    OPTIONAL: LLM enhancement (if Ollama available AND enabled)
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True AND Ollama is available, use LLM for refinement.
                     Default is False - rule-based works well.
        """
        self.use_llm = use_llm

    def refine(self, proposal: AgentProposal) -> AgentProposal:
        """
        Refine proposal content to terse, imperative form.
        """
        # PRIMARY: Rule-based refinement
        refined = self._refine_with_rules(proposal.content, proposal.evidence)

        # OPTIONAL: LLM enhancement
        if self.use_llm:
            llm_refined = self._try_llm_refinement(refined, proposal)
            if llm_refined:
                refined = llm_refined

        proposal.content = refined
        return proposal

    def _refine_with_rules(self, content: str, evidence: List[str]) -> str:
        """
        Refine content using rule-based transformations.
        """
        content_lower = content.lower()

        # Template mappings for common patterns
        REFINEMENT_TEMPLATES = {
            # File operations
            "split": "Plan file splits before writing (200-line limit)",
            "separate": "Plan file splits before writing (200-line limit)",

            # Testing
            "test first": "Write tests before implementation (TDD)",
            "tdd": "Write tests before implementation (TDD)",
            "test before": "Write tests before implementation (TDD)",

            # Output style
            "summary": "Keep summaries 2-3 sentences max",
            "terse": "Keep output terse and actionable",
            "concise": "Keep output concise",
            "short": "Keep explanations short",
            "verbose": "Avoid verbose explanations",

            # Planning
            "plan first": "Create plan before implementation",
            "design first": "Create design docs before coding",
            "plan before": "Create plan before implementation",

            # Error handling
            "log error": "Log errors before returning",
            "error handling": "Handle errors explicitly with logging",
        }

        # Check for template matches
        for keyword, template in REFINEMENT_TEMPLATES.items():
            if keyword in content_lower:
                return template

        # Fallback: Clean up the content
        return self._clean_content(content)

    def _clean_content(self, content: str) -> str:
        """
        Clean content into imperative form.
        """
        # Remove common filler phrases
        FILLER_PATTERNS = [
            r"^continue:?\s*",
            r"^always\s+",
            r"^you\s+should\s+",
            r"^make\s+sure\s+to\s+",
        ]

        result = content
        for pattern in FILLER_PATTERNS:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)

        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]

        # Ensure max length
        words = result.split()
        if len(words) > 12:
            result = ' '.join(words[:12])

        return result

    def _try_llm_refinement(self, content: str, proposal: AgentProposal) -> Optional[str]:
        """
        OPTIONAL: Use Ollama for refinement if available.
        Returns None if LLM unavailable or fails.
        """
        try:
            import requests

            prompt = f"""Refine this rule to terse imperative form (max 10 words):

Rule: {content}
Evidence: {proposal.evidence[0] if proposal.evidence else ""}

Output ONLY the refined rule:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
                timeout=5
            )

            if response.status_code == 200:
                refined = response.json().get("response", "").strip()
                if 3 <= len(refined.split()) <= 12:
                    return refined

        except Exception:
            pass  # LLM unavailable - that's fine

        return None


# ============================================================================
# Main Learning Engine
# ============================================================================

class AgentLearningEngine:
    """
    Main engine for agent self-learning.
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True AND Ollama available, use LLM for refinement.
                     Default is False - rule-based works well.
        """
        self.collector = ObservationCollector()
        self.analyzer = CodebaseAnalyzer()
        self.refiner = ProposalRefiner(use_llm=use_llm)
        self.max_proposals = 5

    def generate_proposals(self, project: Optional[str] = None) -> List[AgentProposal]:
        """
        Generate agent proposals from observations.
        """
        proposals = []

        # Pattern 1: Success reinforcement
        success_proposal = detect_success_pattern(self.collector.observations)
        if success_proposal:
            proposals.append(success_proposal)

        # Pattern 2: Failure avoidance
        failure_proposal = detect_failure_pattern(self.collector.observations)
        if failure_proposal:
            proposals.append(failure_proposal)

        # Pattern 3: Project inference (requires codebase analysis)
        if project:
            codebase_analysis = self.analyzer.analyze(project)
            pattern_proposal = detect_project_pattern(
                self.collector.observations,
                codebase_analysis
            )
            if pattern_proposal:
                proposals.append(pattern_proposal)

        # Pattern 4: Approach reinforcement
        approach_proposal = detect_approach_reinforcement(self.collector.observations)
        if approach_proposal:
            proposals.append(approach_proposal)

        # Refine all proposals
        proposals = [self.refiner.refine(p) for p in proposals]

        # Sort by confidence / priority (higher is better)
        proposals.sort(key=lambda p: p.confidence / p.priority, reverse=True)

        # Take top N
        return proposals[:self.max_proposals]


# ============================================================================
# Integration Functions
# ============================================================================

def generate_agent_proposals(
    observations: List[AgentObservation],
    project: Optional[str] = None,
    use_llm: bool = False
) -> List[AgentProposal]:
    """
    Standalone function for generating agent proposals.

    Args:
        observations: List of agent observations from session
        project: Optional project name for project pattern detection
        use_llm: If True AND Ollama available, use LLM for refinement

    Returns:
        List of refined agent proposals
    """
    engine = AgentLearningEngine(use_llm=use_llm)
    engine.collector.observations = observations
    return engine.generate_proposals(project=project)
