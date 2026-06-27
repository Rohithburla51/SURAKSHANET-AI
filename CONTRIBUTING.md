# 🤝 Contributing to SurakshaNet AI

Thank you for your interest in contributing to SurakshaNet AI! We welcome contributions from developers, designers, researchers, and enthusiasts passionate about fighting financial crime in India.

---

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Ways to Contribute](#ways-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit & PR Guidelines](#commit--pr-guidelines)
- [Testing & QA](#testing--qa)
- [Documentation](#documentation)

---

## Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free experience for all contributors. Please:

- Be respectful and constructive
- Provide thoughtful criticism
- Welcome diverse perspectives
- Report inappropriate behavior to maintainers

---

## Ways to Contribute

### 🐛 Report Bugs
1. Check if the bug is already reported in GitHub Issues
2. Include:
   - Clear description of the issue
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots/logs (if applicable)
   - Your environment (OS, browser, Python version, etc.)

### 💡 Suggest Features
1. Check the roadmap in `README.md`
2. Create a GitHub Issue with:
   - Clear title and description
   - Use case / why it's needed
   - Proposed solution (if any)
   - Alternatives considered

### 📝 Improve Documentation
- Fix typos or clarify confusing sections
- Add examples or diagrams
- Translate docs to Indian languages
- Update deployment guides

### 🧠 Improve ML Models
- Enhance scam detection accuracy
- Add new counterfeit detection techniques
- Optimize Cypher query generation
- Expand training data for RAG corpus

### 🎨 UI/UX Improvements
- Cross-browser testing and fixes
- Accessibility improvements (WCAG compliance)
- Mobile responsiveness
- Dark mode refinements

### 🔐 Security Audits
- Report security vulnerabilities responsibly (see Security Policy)
- Suggest input validation improvements
- Review authentication/authorization logic
- Audit dependency versions

---

## Development Setup

### Prerequisites
- Node.js 18+
- Python 3.10+
- Git
- GitHub account

### Step 1: Fork & Clone
```bash
# Fork the repo on GitHub

# Clone your fork
git clone https://github.com/YOUR_USERNAME/surakshanet-ai.git
cd surakshanet-ai

# Add upstream remote
git remote add upstream https://github.com/OriginalOrg/surakshanet-ai.git
```

### Step 2: Create Feature Branch
```bash
# Update main
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

Branch naming convention:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation
- `refactor/` — Code restructuring
- `perf/` — Performance improvements
- `test/` — Testing improvements

### Step 3: Local Development

**Backend**:
```bash
# Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio flake8 black mypy

# Run backend in demo mode
cd backend
export DEMO_MOCK_MODE=true
uvicorn main:app --reload --port 8000
```

**Frontend**:
```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# In another terminal, run linter
npm run lint
```

---

## Coding Standards

### Python (Backend)

**Style**:
- Follow PEP 8
- Use Black for formatting:
  ```bash
  black backend/
  ```
- Use type hints:
  ```python
  async def analyze_scam(text: str) -> ScamAnalysisResult:
      pass
  ```

**Naming**:
- `ClassName` for classes
- `function_name` for functions
- `CONSTANT_NAME` for constants
- `_private_method` for internal methods

**Docstrings**:
```python
def analyze_scam(text: str) -> ScamAnalysisResult:
    """
    Analyze text for scam indicators using Groq inference.
    
    Args:
        text: Input text to analyze (max 1000 chars)
        
    Returns:
        ScamAnalysisResult with risk_score (0-100), category, tactics
        
    Raises:
        ValueError: If text is empty or too long
        GroqError: If inference fails (falls back to demo mode)
    """
    pass
```

### TypeScript/React (Frontend)

**Style**:
- Follow ESLint config in `.eslintrc.json`
- Use Prettier for formatting:
  ```bash
  npm run format
  ```
- Use strict TypeScript (`strict: true` in tsconfig.json)

**Components**:
```typescript
interface ComponentProps {
  /** Description of prop */
  score: number;
  onAnalyze?: (result: AnalysisResult) => void;
}

export function MyComponent({ score, onAnalyze }: ComponentProps) {
  return <div>{score}</div>;
}
```

**Hooks**:
```typescript
// Use React hooks for state management
const [loading, setLoading] = useState(false);

useEffect(() => {
  // Effect implementation
}, [dependency]);
```

---

## Commit & PR Guidelines

### Commit Messages

Format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (no logic change)
- `refactor`: Code restructuring
- `perf`: Performance improvement
- `test`: Test addition/modification
- `chore`: Build config, deps, etc.

Examples:
```bash
git commit -m "feat(scam): add hindi language support to risk analysis"
git commit -m "fix(bank): resolve watermark opacity calculation bug"
git commit -m "docs: update deployment guide for HF Spaces"
```

### Pull Requests

**Before submitting:**
1. Ensure code is formatted (Black for Python, Prettier for TS)
2. Run linters (flake8 for Python, ESLint for TS)
3. Type-check (mypy for Python, TypeScript for TS)
4. Test locally (including demo mode)
5. Update `CHANGELOG.md` if applicable

**PR Description Template**:
```markdown
## Description
Brief description of changes

## Related Issues
Fixes #123

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added
- [ ] Tested with demo data
- [ ] Tested with real APIs
- [ ] Cross-browser tested

## Screenshots (if applicable)
[Add screenshots of UI changes]

## Checklist
- [ ] Code follows project style
- [ ] No TypeScript/Python errors
- [ ] Linter passes
- [ ] Tests pass
- [ ] Documentation updated
```

---

## Testing & QA

### Backend Testing

```bash
# Unit tests
pytest backend/tests/

# With coverage
pytest --cov=backend backend/tests/

# Type checking
mypy backend/

# Linting
flake8 backend/
```

### Frontend Testing

```bash
# Lint
npm run lint

# Type check
npm run type-check

# Build
npm run build
```

### Manual Testing

**Scam Analysis Portal**:
- [ ] Text input with demo message
- [ ] Audio file upload
- [ ] Risk gauge animation
- [ ] Bilingual output
- [ ] Demo mode toggle

**Bank Teller Portal**:
- [ ] Image upload (valid formats)
- [ ] File size validation (15MB limit)
- [ ] Denomination selection
- [ ] Verdict banner display
- [ ] Forensic metrics chart

**Police Dashboard**:
- [ ] Natural language query
- [ ] Phone/account trace
- [ ] Network graph rendering
- [ ] Node color coding
- [ ] Cypher query display

---

## Documentation

### Types of Documentation

1. **Code Comments**: Explain the "why", not the "what"
   ```python
   # Good: Explains why we're rate limiting
   # Groq free tier has 14k requests/day limit
   @limiter.limit("100/hour")
   
   # Bad: Just repeats the code
   # Rate limit to 100 per hour
   @limiter.limit("100/hour")
   ```

2. **Docstrings**: Document functions, classes, modules
   ```python
   """
   Analyze scam text using vector RAG + Groq inference.
   
   Args:
       text: Suspicious text message
       
   Returns:
       Risk score (0-100), category, manipulation tactics
   """
   ```

3. **README.md**: Project overview, setup, usage
4. **DEPLOYMENT.md**: Deployment instructions
5. **Architecture Docs**: Design decisions, data flow

### Adding Docs

```bash
# Create new documentation file
touch docs/my-feature.md

# Build docs locally
cd docs && make html
```

---

## Process for Getting Contributions Merged

1. **Submit PR** with clear description and related issue #
2. **CI Checks**: GitHub Actions must pass
3. **Code Review**: Maintainers review for:
   - Code quality
   - Adherence to standards
   - Test coverage
   - Documentation
4. **Requested Changes**: Address feedback (may take 1-2 iterations)
5. **Approval**: Maintainer approves
6. **Merge**: Maintainer squash-merges to main

---

## Recognition

Contributors are recognized in:
- GitHub `CONTRIBUTORS.md` file
- Release notes
- Project README (if significant contribution)

---

## Questions or Need Help?

- Open a GitHub Discussion
- Email: maintainers@surakshanet.dev
- Join our Discord (link in README)

---

## License

By contributing, you agree that your contributions are licensed under the same MIT License as the project.

---

**Thank you for making SurakshaNet AI better! 🙏**

---

*Last Updated: June 27, 2026*
