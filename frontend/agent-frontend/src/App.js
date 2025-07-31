import React, { useState } from 'react';
import './App.css';

// This is a simplified frontend that assumes tool parameters for this demo.
// A real app would generate these forms dynamically.
const MOCK_TOOL_PARAMS = {
  external_rest: ['url', 'auth_token'],
  document_tool: ['file_name'],
  calculator_tool: [],
};

function App() {
  const [phase, setPhase] = useState('START'); // START, PLANNING, CONFIGURING, DONE
  const [agentName, setAgentName] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [goal, setGoal] = useState('');
  
  const [plan, setPlan] = useState([]);
  const [currentToolIndex, setCurrentToolIndex] = useState(0);
  const [configuredTools, setConfiguredTools] = useState([]);

  const [finalConfig, setFinalConfig] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // API call to generate the plan
  const handleCreatePlan = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:8000/generate-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });
      if (!response.ok) throw new Error('Failed to generate plan.');
      const data = await response.json();
      setPlan(data.planned_tools);
      setPhase('PLANNING');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Handles configuration of a single tool
  const handleConfigureTool = (e) => {
    e.preventDefault();
    const toolName = plan[currentToolIndex];
    const params = MOCK_TOOL_PARAMS[toolName] || [];
    const newConfig = { tool_name: toolName, parameters: {} };

    params.forEach(param => {
      newConfig.parameters[param] = e.target[param]?.value || null;
    });

    const updatedTools = [...configuredTools, newConfig];
    setConfiguredTools(updatedTools);

    // Move to the next tool or finalize
    if (currentToolIndex < plan.length - 1) {
      setCurrentToolIndex(currentToolIndex + 1);
    } else {
      handleFinalize(updatedTools);
    }
  };

  // API call to finalize the agent configuration
  const handleFinalize = async (finalTools) => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch('http://127.0.0.1:8000/finalize-agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: agentName,
          description: agentDescription,
          goal: goal,
          configured_tools: finalTools,
        }),
      });
      if (!response.ok) throw new Error('Failed to finalize configuration.');
      const data = await response.json();
      setFinalConfig(data);
      setPhase('DONE');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const renderPhase = () => {
    if (isLoading) return <div className="spinner"></div>;

    switch (phase) {
      case 'START':
        return (
          <form onSubmit={handleCreatePlan}>
            <h2>1. Define Your Agent</h2>
            <input type="text" value={agentName} onChange={(e) => setAgentName(e.target.value)} placeholder="Agent Name (e.g., Sales Assistant)" required />
            <input type="text" value={agentDescription} onChange={(e) => setAgentDescription(e.target.value)} placeholder="Agent Description" required />
            <textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Describe the agent's workflow goal..." required />
            <button type="submit">Create Plan</button>
          </form>
        );

      case 'PLANNING':
        return (
          <div>
            <h2>2. Approve the Plan</h2>
            <p>Based on your goal, the agent will be configured with these tools:</p>
            <ul className="plan-list">
              {plan.map((tool, index) => <li key={index}>{tool}</li>)}
            </ul>
            <button onClick={() => setPhase('CONFIGURING')}>Approve and Configure</button>
          </div>
        );
        
      case 'CONFIGURING':
        const currentTool = plan[currentToolIndex];
        const params = MOCK_TOOL_PARAMS[currentTool] || [];
        return (
          <form onSubmit={handleConfigureTool}>
            <h2>3. Configure: <span>{currentTool}</span></h2>
            {params.length > 0 ? (
              params.map(param => (
                <input key={param} name={param} type="text" placeholder={`Enter static value for ${param}`} />
              ))
            ) : (
              <p>This tool requires no static parameters.</p>
            )}
            <button type="submit">
              {currentToolIndex < plan.length - 1 ? 'Save and Configure Next' : 'Save and Finalize'}
            </button>
          </form>
        );

      case 'DONE':
        return (
          <div>
            <h2>Configuration Complete!</h2>
            <p>This JSON will be sent to Oracle AI Agent Studio which will have your agent ready to test!</p>
            <pre>{JSON.stringify(finalConfig, null, 2)}</pre>
            <button onClick={() => window.location.reload()}>Start Over</button>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="container">
      <header>
        <h1>AI Agent Studio Builder</h1>
        <p>Create an agent configuration for your AI agent by describing its workflow.</p>
      </header>
      <main>
        {error && <div className="error-box">{error}</div>}
        {renderPhase()}
      </main>
    </div>
  );
}

export default App;