"""
Test the RealAI Hierarchical Agent System
"""

def test_structure():
    """Test that the package structure is correct."""
    print("🧪 Testing RealAI Hierarchical Agent System structure...")

    try:
        # Test that we can import the package
        import realai_agent
        print("✅ Package imported successfully")

        # Test that key attributes exist
        assert hasattr(realai_agent, 'get_llm'), "get_llm function should exist"
        print("✅ get_llm function exists")

        assert hasattr(realai_agent, '__version__'), "Version should exist"
        print("✅ Version exists")

        # Test that we can import individual modules without initializing LLM
        import sys
        import os
        sys.path.insert(0, os.path.dirname(realai_agent.__file__))

        # Test tools module
        import tools
        assert hasattr(tools, 'TOOL_REGISTRY'), "TOOL_REGISTRY should exist"
        assert len(tools.TOOL_REGISTRY) >= 9, f"Expected at least 9 tools, got {len(tools.TOOL_REGISTRY)}"
        print("✅ Tools module loaded correctly")

        # Test agents module structure
        import agents
        assert hasattr(agents, 'get_agent_registry'), "get_agent_registry function should exist"
        registry = agents.get_agent_registry()
        assert len(registry) == 5, f"Expected 5 agents, got {len(registry)}"
        print("✅ Agents module loaded correctly")

        print("🎉 All hierarchical agent structure tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    test_structure()