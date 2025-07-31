import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [phase, setPhase] = useState('START'); // START, PLANNING, CONFIGURING, DONE
  const [agentName, setAgentName] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [goal, setGoal] = useState('');

  const [plan, setPlan] = useState([]);
  const [currentToolIndex, setCurrentToolIndex] = useState(0);
  const [configuredTools, setConfiguredTools] = useState([]);

  const [toolMetadata, setToolMetadata] = useState({}); // Stores dynamic tool metadata
  const [currentToolParams, setCurrentToolParams] = useState({}); // Stores current tool's form inputs

  const [finalConfig, setFinalConfig] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const API_BASE_URL = 'http://127.0.0.1:8000'; // The mcp_client URL

  // Fetch tool metadata on component mount
  useEffect(() => {
    const fetchToolMetadata = async () => {
      try {
        // Frontend calls mcp_client, which then calls mcp_server for tools
        const response = await fetch(`${API_BASE_URL}/get-tools-metadata`);
        if (!response.ok) throw new Error('Failed to fetch tool metadata.');
        const data = await response.json();
        
        const metadataMap = {};
        data.tools.forEach(tool => {
          metadataMap[tool.tool_name] = tool;
        });
        setToolMetadata(metadataMap);
      } catch (err) {
        setError("Failed to load tool definitions: " + err.message);
      }
    };
    fetchToolMetadata();
  }, []); // Empty dependency array means this runs once on mount

  // API call to generate the plan
  const handleCreatePlan = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/generate-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate plan.');
      }
      const data = await response.json();
      setPlan(data.planned_tools);
      setCurrentToolIndex(0); // Reset for new plan
      setConfiguredTools([]); // Clear previous configurations
      setPhase('PLANNING');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // Handles configuration of a single tool
  const handleConfigureTool = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    const toolName = plan[currentToolIndex];
    
    // Create the new tool configuration
    const newConfig = { tool_name: toolName, parameters: { ...currentToolParams } };
    const updatedTools = [...configuredTools, newConfig];
    setConfiguredTools(updatedTools);
    setCurrentToolParams({}); // Clear current tool params for the next tool

    // Move to the next tool or finalize
    if (currentToolIndex < plan.length - 1) {
      setCurrentToolIndex(currentToolIndex + 1);
      setPhase('CONFIGURING'); // Stay in configuring phase
      setIsLoading(false);
    } else {
      await handleFinalize(updatedTools);
    }
  };

  // API call to finalize the agent configuration
  const handleFinalize = async (finalTools) => {
    setIsLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE_URL}/finalize-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_name: agentName,
          description: agentDescription,
          goal: goal,
          configured_tools: finalTools,
        }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to finalize configuration.');
      }
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
            {plan.length > 0 ? (
                <ul className="plan-list">
                    {plan.map((tool, index) => <li key={index}>{tool}</li>)}
                </ul>
            ) : (
                <p>No specific tools were identified for this goal. You can still proceed or refine your goal.</p>
            )}
            <button onClick={() => setPhase('CONFIGURING')}>Approve and Configure</button>
          </div>
        );

      case 'CONFIGURING':
        const currentToolName = plan[currentToolIndex];
        const toolInfo = toolMetadata[currentToolName];
        
        if (!toolInfo) {
          return <p>Loading tool details or tool not found: {currentToolName}</p>;
        }

        return (
          <form onSubmit={handleConfigureTool}>
            <h2>3. Configure: <span>{toolInfo.tool_name}</span></h2>
            <p className="tool-description">{toolInfo.description}</p>
            
            {toolInfo.parameters.length > 0 ? (
              toolInfo.parameters.map(param => (
                <div key={param.name} className="param-input">
                  <label>
                    {param.name} ({param.type}) {param.optional ? '(Optional)' : '(Required)'}:
                  </label>
                  {param.name === 'file_name' && toolInfo.tool_name === 'document_tool' ? (
                      // Special handling for file_name to get local file input
                      <>
                        <input
                          type="text"
                          value={currentToolParams[param.name] || ''}
                          onChange={(e) => setCurrentToolParams({ ...currentToolParams, [param.name]: e.target.value })}
                          placeholder={`Enter file name (e.g., my_report.pdf)`}
                          required={!param.optional}
                        />
                        <small>For demo, you'll provide content as text later, but specify a filename here.</small>
                        <textarea
                            value={currentToolParams['file_content'] || ''}
                            onChange={(e) => setCurrentToolParams({ ...currentToolParams, 'file_content': e.target.value })}
                            placeholder="Enter the document content here for demo purposes"
                            rows="5"
                            required={!param.optional && param.name === 'file_name'} // file_content is required if file_name is for document_tool
                        ></textarea>
                         <small>Note: In a real app, this would be a file upload, not text input.</small>
                      </>
                  ) : (
                    <input
                      type="text"
                      value={currentToolParams[param.name] || ''}
                      onChange={(e) => setCurrentToolParams({ ...currentToolParams, [param.name]: e.target.value })}
                      placeholder={`Enter value for ${param.name}`}
                      required={!param.optional}
                    />
                  )}
                </div>
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
            <p>This JSON can be used to configure your Oracle AI Agent Studio agent:</p>
            <pre className="json-output">{JSON.stringify(finalConfig, null, 2)}</pre>
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



// import React, { useState } from 'react';
// import './App.css';

// // This is a simplified frontend that assumes tool parameters for this demo.
// // A real app would generate these forms dynamically.
// const MOCK_TOOL_PARAMS = {
//   external_rest: ['url', 'auth_token'],
//   document_tool: ['file_name'],
//   calculator_tool: [],
// };

// function App() {
//   const [phase, setPhase] = useState('START'); // START, PLANNING, CONFIGURING, DONE
//   const [agentName, setAgentName] = useState('');
//   const [agentDescription, setAgentDescription] = useState('');
//   const [goal, setGoal] = useState('');
  
//   const [plan, setPlan] = useState([]);
//   const [currentToolIndex, setCurrentToolIndex] = useState(0);
//   const [configuredTools, setConfiguredTools] = useState([]);

//   const [finalConfig, setFinalConfig] = useState(null);
//   const [error, setError] = useState('');
//   const [isLoading, setIsLoading] = useState(false);

//   // API call to generate the plan
//   const handleCreatePlan = async (e) => {
//     e.preventDefault();
//     setIsLoading(true);
//     setError('');
//     try {
//       const response = await fetch('http://127.0.0.1:8000/generate-plan', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ goal }),
//       });
//       if (!response.ok) throw new Error('Failed to generate plan.');
//       const data = await response.json();
//       setPlan(data.planned_tools);
//       setPhase('PLANNING');
//     } catch (err) {
//       setError(err.message);
//     } finally {
//       setIsLoading(false);
//     }
//   };
  
//   // Handles configuration of a single tool
//   const handleConfigureTool = (e) => {
//     e.preventDefault();
//     const toolName = plan[currentToolIndex];
//     const params = MOCK_TOOL_PARAMS[toolName] || [];
//     const newConfig = { tool_name: toolName, parameters: {} };

//     params.forEach(param => {
//       newConfig.parameters[param] = e.target[param]?.value || null;
//     });

//     const updatedTools = [...configuredTools, newConfig];
//     setConfiguredTools(updatedTools);

//     // Move to the next tool or finalize
//     if (currentToolIndex < plan.length - 1) {
//       setCurrentToolIndex(currentToolIndex + 1);
//     } else {
//       handleFinalize(updatedTools);
//     }
//   };

//   // API call to finalize the agent configuration
//   const handleFinalize = async (finalTools) => {
//     setIsLoading(true);
//     setError('');
//     try {
//       const response = await fetch('http://127.0.0.1:8000/finalize-agent', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({
//           agent_name: agentName,
//           description: agentDescription,
//           goal: goal,
//           configured_tools: finalTools,
//         }),
//       });
//       if (!response.ok) throw new Error('Failed to finalize configuration.');
//       const data = await response.json();
//       setFinalConfig(data);
//       setPhase('DONE');
//     } catch (err) {
//       setError(err.message);
//     } finally {
//       setIsLoading(false);
//     }
//   };

//   const renderPhase = () => {
//     if (isLoading) return <div className="spinner"></div>;

//     switch (phase) {
//       case 'START':
//         return (
//           <form onSubmit={handleCreatePlan}>
//             <h2>1. Define Your Agent</h2>
//             <input type="text" value={agentName} onChange={(e) => setAgentName(e.target.value)} placeholder="Agent Name (e.g., Sales Assistant)" required />
//             <input type="text" value={agentDescription} onChange={(e) => setAgentDescription(e.target.value)} placeholder="Agent Description" required />
//             <textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Describe the agent's workflow goal..." required />
//             <button type="submit">Create Plan</button>
//           </form>
//         );

//       case 'PLANNING':
//         return (
//           <div>
//             <h2>2. Approve the Plan</h2>
//             <p>Based on your goal, the agent will be configured with these tools:</p>
//             <ul className="plan-list">
//               {plan.map((tool, index) => <li key={index}>{tool}</li>)}
//             </ul>
//             <button onClick={() => setPhase('CONFIGURING')}>Approve and Configure</button>
//           </div>
//         );
        
//       case 'CONFIGURING':
//         const currentTool = plan[currentToolIndex];
//         const params = MOCK_TOOL_PARAMS[currentTool] || [];
//         return (
//           <form onSubmit={handleConfigureTool}>
//             <h2>3. Configure: <span>{currentTool}</span></h2>
//             {params.length > 0 ? (
//               params.map(param => (
//                 <input key={param} name={param} type="text" placeholder={`Enter static value for ${param}`} />
//               ))
//             ) : (
//               <p>This tool requires no static parameters.</p>
//             )}
//             <button type="submit">
//               {currentToolIndex < plan.length - 1 ? 'Save and Configure Next' : 'Save and Finalize'}
//             </button>
//           </form>
//         );

//       case 'DONE':
//         return (
//           <div>
//             <h2>Configuration Complete!</h2>
//             <p>This JSON will be sent to Oracle AI Agent Studio which will have your agent ready to test!</p>
//             <pre>{JSON.stringify(finalConfig, null, 2)}</pre>
//             <button onClick={() => window.location.reload()}>Start Over</button>
//           </div>
//         );

//       default:
//         return null;
//     }
//   };

//   return (
//     <div className="container">
//       <header>
//         <h1>AI Agent Studio Builder</h1>
//         <p>Create an agent configuration for your AI agent by describing its workflow.</p>
//       </header>
//       <main>
//         {error && <div className="error-box">{error}</div>}
//         {renderPhase()}
//       </main>
//     </div>
//   );
// }

// export default App;