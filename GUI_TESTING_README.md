# Othello Coach GUI Testing Suite

This comprehensive testing suite ensures all GUI features promised in the v1.0 and v1.1 roadmaps are properly implemented and integrated.

## 🎯 What This Test Suite Covers

### Core GUI Features (v1.0)
- ✅ Main window creation and layout
- ✅ Board widget functionality (moves, undo, redo)
- ✅ Game controls integration
- ✅ Insights dock with overlay toggles
- ✅ Tree view functionality

### Insights System (v1.0)
- ✅ Feature extraction (mobility, parity, stability, corner access)
- ✅ Rationale generation for moves
- ✅ Mistake taxonomy classification
- ✅ All overlay types (mobility heat, parity map, stability heat, corner tension)

### Tree System (v1.0)
- ✅ Preset-based tree building
- ✅ GDL-based tree building
- ✅ Tree export (DOT, PNG formats)
- ✅ Tree visualization

### Training System (v1.1)
- ✅ Trainer initialization with Leitner scheduling
- ✅ Training session generation
- ✅ Training dock UI components
- ✅ Integration with insights

### Gauntlet System (v1.1)
- ✅ Glicko-2 rating system
- ✅ Gauntlet runner with strength profiles
- ✅ Self-play integration

### Novelty System (v1.1)
- ✅ Novelty radar initialization
- ✅ Novelty scoring algorithms
- ✅ Integration with tree building

### API System (v1.1)
- ✅ Local API server creation
- ✅ Required endpoints (/health, /analyse, /tree, /game/{id})
- ✅ Authentication and rate limiting

### Integration Features
- ✅ Insights with tree building
- ✅ Training with insights
- ✅ Novelty with trees

### Performance Requirements
- ✅ Overlay latency ≤150ms
- ✅ Tree building performance
- ✅ Search performance

### Error Handling
- ✅ Invalid move handling
- ✅ Empty tree handling
- ✅ API error handling

## 🚀 Quick Start

### 1. Run Quick Test First
```bash
python test_gui_quick.py
```
This verifies basic functionality before running comprehensive tests.

### 2. Install Test Dependencies
```bash
pip install -r test_requirements.txt
```

### 3. Run Comprehensive Tests
```bash
python run_gui_tests.py
```

### 4. Run Specific Test Suites
```bash
# Test only core GUI features
python run_gui_tests.py TestGUICoreFeatures

# Test only insights system
python run_gui_tests.py TestInsightsSystem

# Test only training system
python run_gui_tests.py TestTrainingSystem
```

## 📊 Test Coverage

The test suite provides comprehensive coverage reporting:
- **Terminal output**: Shows missing lines
- **HTML report**: `htmlcov/index.html` - Interactive coverage browser
- **XML report**: `coverage.xml` - For CI/CD integration

## 🧪 Test Structure

### TestGUICoreFeatures
Tests basic GUI functionality without external dependencies.

### TestInsightsSystem
Tests the insights engine (features, rationale, taxonomy, overlays).

### TestTreeSystem
Tests tree building and visualization capabilities.

### TestTrainingSystem
Tests the training system and spaced repetition.

### TestGauntletSystem
Tests rating system and self-play capabilities.

### TestNoveltySystem
Tests novelty detection and scoring.

### TestAPISystem
Tests local API functionality.

### TestIntegrationFeatures
Tests how different systems work together.

### TestPerformanceRequirements
Tests performance benchmarks from roadmaps.

### TestErrorHandling
Tests error handling and edge cases.

## 🔧 Configuration

### pytest.ini
- Sets up Qt testing environment
- Configures coverage reporting
- Sets test timeouts and markers

### Environment Variables
- `QT_QPA_PLATFORM=offscreen` - Headless testing
- `OTHELLO_COACH_TESTING=1` - Test mode flag

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're in the project root directory
   - Check that virtual environment is activated
   - Verify all dependencies are installed

2. **Qt Platform Issues**
   - On Windows: Ensure PyQt6 is properly installed
   - On Linux: May need additional Qt dependencies
   - Use `QT_QPA_PLATFORM=offscreen` for headless testing

3. **Performance Test Failures**
   - Tests may fail on slower machines
   - Adjust timeout values in `pytest.ini` if needed
   - Performance requirements are based on modern hardware

### Debug Mode
```bash
# Run with verbose output
pytest tests/test_gui_comprehensive.py -v -s

# Run single test with debugger
pytest tests/test_gui_comprehensive.py::TestGUICoreFeatures::test_main_window_creation -s
```

## 📈 Adding New Tests

### For New Features
1. Add test class to appropriate section
2. Follow naming convention: `test_feature_name`
3. Include both positive and negative test cases
4. Test integration with existing systems

### For Bug Fixes
1. Create test that reproduces the bug
2. Verify test fails before fix
3. Apply fix
4. Verify test passes

## 🎯 Success Criteria

A successful test run means:
- ✅ All tests pass
- ✅ Coverage ≥80%
- ✅ Performance requirements met
- ✅ Integration tests pass
- ✅ Error handling works correctly

## 📚 Related Documentation

- [v1.0 Roadmap](roadmaps/v1-0.txt)
- [v1.1 Roadmap](roadmaps/v1-1.txt)
- [Main README](README.md)
- [API Documentation](othello_coach/api/)

## 🤝 Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all existing tests pass
3. Add integration tests for new features
4. Update this README if needed

## 📞 Support

If tests fail or you need help:
1. Check the quick test first: `python test_gui_quick.py`
2. Review error messages and stack traces
3. Check that all dependencies are installed
4. Verify you're in the correct directory
5. Check that virtual environment is activated
