import { useEffect, useState } from 'react';
import mermaid from 'mermaid';

let cachedPatternsSvg: string | null = null;
let cachedStepsSvg: string | null = null;
let mermaidInitialized = false;

const patternsDiagram = `
flowchart TD
    classDef startClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:3px,font-size:16px
    classDef decisionClass fill:#fff3e0,stroke:#e65100,stroke-width:1px,font-size:10px
    classDef smallDecisionClass fill:#fff3e0,stroke:#e65100,stroke-width:1px,font-size:9px
    classDef processClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,font-size:13px
    classDef optionalClass fill:#ffffff,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5,font-size:10px
    classDef endClass fill:#ffebee,stroke:#b71c1c,stroke-width:2px,font-size:15px
    Start([Start Deployment Configuration]) --> ChooseMode{Choose<br/>Configuration<br/>Mode?}
    ChooseMode -->|PXE Upload| PxeUpload[Upload PXE Mapping File]
    ChooseMode -->|Manual| Manual[Manual Configuration]
    PxeUpload --> ChooseCluster{Select<br/>Cluster<br/>Type?}
    Manual --> ChooseCluster
    ChooseCluster -->|Slurm| Slurm[Slurm Only]
    ChooseCluster -->|K8s| K8s[Kubernetes Only]
    ChooseCluster -->|Both| Both[Slurm + Kubernetes]
    K8s --> EnableHA{Enable HA?}
    Both --> EnableHA
    EnableHA -->|Yes| HaConfig[Configure HA]
    EnableHA -->|No| OptionalFeatures{Enable<br/>Optional<br/>Features?}
    Slurm --> OptionalFeatures
    K8s --> OptionalFeatures
    Both --> OptionalFeatures
    HaConfig --> OptionalFeatures
    OptionalFeatures -->|Cloud-Init| CloudInit[Cloud-Init Configuration]
    OptionalFeatures -->|Telemetry| Telemetry[Telemetry Configuration]
    OptionalFeatures -->|Build Stream / GitLab| BuildStreamGitLab[Build Stream / GitLab Configuration]
    OptionalFeatures -->|BMC Discovery| BmcDiscovery[BMC Discovery Flow]
    BmcDiscovery --> BmcCredentials[BMC Credentials]
    BmcCredentials --> BmcNetwork[Network Configuration]
    BmcNetwork --> BmcGenerate[Run discovery playbook and generate bmc_pxe_mapping_file.csv]
    BmcGenerate -->|Return to| ChooseMode
    class Start startClass
    class ChooseMode,ChooseCluster,OptionalFeatures smallDecisionClass
    class EnableHA decisionClass
    class PxeUpload,Manual,Slurm,K8s,Both,HaConfig processClass
    class CloudInit,Telemetry,BuildStreamGitLab,BmcDiscovery,BmcCredentials,BmcNetwork,BmcGenerate optionalClass
`;

const wizardStepsDiagram = `
flowchart TD
    classDef optional fill:#ffffff,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5
    subgraph Row1[ ]
        direction LR
        S1[1. Deployment Setup] --> S2[2. PXE Functional Groups] --> S3[3. Network Configuration] --> S4[4. Storage Configuration]
    end
    subgraph Row2[ ]
        direction LR
        S5[5. Cloud-Init Configuration] --> S6[6. Omnia Cluster Configuration] --> S7[7. Telemetry Configuration] --> S8[8. Build Stream Configuration] --> S9[9. Summary & Generate]
    end
    S4 --> S5
    class S5,S7,S8 optional
`;

const DeploymentOverview = () => {
  const [patternsSvg, setPatternsSvg] = useState(cachedPatternsSvg);
  const [stepsSvg, setStepsSvg] = useState(cachedStepsSvg);

  useEffect(() => {
    if (cachedPatternsSvg && cachedStepsSvg) return;

    if (!mermaidInitialized) {
      mermaid.initialize({ startOnLoad: false });
      mermaidInitialized = true;
    }

    if (!cachedPatternsSvg) {
      mermaid.render('deployment-patterns-diagram', patternsDiagram)
        .then(({ svg }) => {
          cachedPatternsSvg = svg;
          setPatternsSvg(svg);
        })
        .catch((err) => console.error('Failed to render patterns diagram:', err));
    }

    if (!cachedStepsSvg) {
      mermaid.render('deployment-wizard-steps-diagram', wizardStepsDiagram)
        .then(({ svg }) => {
          cachedStepsSvg = svg;
          setStepsSvg(svg);
        })
        .catch((err) => console.error('Failed to render wizard steps diagram:', err));
    }
  }, []);

  return (
    <div className="space-y-6">
      <div className="space-y-6">
        <p className="wizard-description">
          This flowchart shows the high-level deployment configuration patterns available in the wizard.
        </p>
        <p className="visually-hidden">
          This diagram describes the deployment configuration flow: start by choosing a configuration mode
          (PXE Upload or Manual) and a cluster type, optionally enable high availability, and enable optional
          features such as Cloud-Init, Telemetry, Build Stream/GitLab, and BMC Discovery. The BMC Discovery
          flow runs a discovery playbook and generates a bmc_pxe_mapping_file.csv, then returns to choose the
          configuration mode.
        </p>
        {patternsSvg ? (
          <div dangerouslySetInnerHTML={{ __html: patternsSvg }} />
        ) : (
          <p className="wizard-description">Loading diagram...</p>
        )}
      </div>

      <div className="space-y-6">
        <h2>Wizard Steps</h2>
        <p className="wizard-description">
          The wizard walks through these steps in order.
        </p>
        <p className="visually-hidden">
          This diagram lists the wizard steps in order: Deployment Setup, PXE Functional Groups, Network
          Configuration, Storage Configuration, Cloud-Init Configuration, Omnia Cluster Configuration, Telemetry
          Configuration, Build Stream Configuration, and Summary & Generate.
          Cloud-Init, Telemetry, and Build Stream are optional.
        </p>
        {stepsSvg ? (
          <div dangerouslySetInnerHTML={{ __html: stepsSvg }} />
        ) : (
          <p className="wizard-description">Loading diagram...</p>
        )}
      </div>
    </div>
  );
};

export default DeploymentOverview;
