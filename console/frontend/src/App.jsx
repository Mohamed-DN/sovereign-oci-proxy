import React, { useState } from 'react';
import { AuthProvider } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Overview from './components/Overview';
import Topology3D from './components/Topology3D';
import NodeMatrix from './components/NodeMatrix';
import NodeActions from './components/NodeActions';
import NeroDrop from './components/NeroDrop';
import UserManagement from './components/UserManagement';
import AppBundles from './components/AppBundles';
import PeeringManagement from './components/PeeringManagement';
import BehavioralRiskDashboard from './components/BehavioralRiskDashboard';
import GeoFencingMap from './components/GeoFencingMap';
import NeroNukePanel from './components/NeroNukePanel';
import NeroNukeSecretAccessModal from './components/NeroNukeSecretAccessModal';
import CryptoConfigModal from './components/CryptoConfigModal';
import SettingsACL from './components/SettingsACL';
import AuditLogs from './components/AuditLogs';
import { Settings, Shield, Terminal, Cpu, CheckCircle2 } from 'lucide-react';

function MeshSettingsView() {
  return (
    <div className="space-y-6 font-mono">
      <div>
        <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
          <span>Sovereign Mesh Global Configuration</span>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent-primary/20 text-accent-primary border border-accent-primary/40">
            System Parameters
          </span>
        </h1>
        <p className="text-xs text-slate-400 mt-1 font-sans">
          Low-level cryptographic primitives, MTU sizing, and relay anycast tuning.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 font-bold text-slate-100 text-sm">
            <Shield className="w-4 h-4 text-accent-primary" />
            <span>Cryptographic Ciphersuites</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Tunnel Protocol:</span>
              <span className="text-accent-primary font-bold">Noise_IKpsk2_25519_ChaChaPoly</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Key Exchange:</span>
              <span className="text-slate-200">Curve25519 (Clamped Scalar)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Symmetric Cipher:</span>
              <span className="text-slate-200">ChaCha20-Poly1305 (256-bit AEAD)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">P2P File Hashing:</span>
              <span className="text-emerald-400 font-bold">BLAKE3 (64KB Chunks)</span>
            </div>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 font-bold text-slate-100 text-sm">
            <Terminal className="w-4 h-4 text-violet-400" />
            <span>Overlay Network Tuning</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Tunnel MTU:</span>
              <span className="text-slate-200">1380 Bytes (Optimized for OCI/AWS encapsulation)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Keepalive Interval:</span>
              <span className="text-slate-200">25 Seconds (NAT Hole Punching)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Local Staging Binding:</span>
              <span className="text-accent-primary">127.0.0.1:8081 (UI) / 8082 (API)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex justify-between">
              <span className="text-slate-400">Tailscale Isolation:</span>
              <span className="text-emerald-400 font-bold">PASSTHROUGH_SAFE (Zero utunX touches)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MainConsole() {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedNode, setSelectedNode] = useState(null);
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [isSecretModalOpen, setIsSecretModalOpen] = useState(false);

  // Persistent Red Button State for NeroNuke (Visible on EVERY page when armed)
  const [nukeArmed, setNukeArmed] = useState(false);
  const [nukeScheduledAt, setNukeScheduledAt] = useState(null);

  const handleArmNuke = (scheduledAt) => {
    setNukeArmed(true);
    setNukeScheduledAt(scheduledAt);
  };

  const handleDisarmNuke = () => {
    setNukeArmed(false);
    setNukeScheduledAt(null);
  };

  const renderActiveView = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <Overview
            onSelectNode={(node) => setSelectedNode(node)}
            onNavigateTab={(tab) => setActiveTab(tab)}
          />
        );
      case 'topology':
        return <Topology3D onSelectNode={(node) => setSelectedNode(node)} />;
      case 'nodes':
        return (
          <NodeMatrix
            onSelectNode={(node) => setSelectedNode(node)}
            onOpenEnrollModal={() => setIsEnrollModalOpen(true)}
          />
        );
      case 'peering':
        return <PeeringManagement />;
      case 'geofencing':
        return <GeoFencingMap />;
      case 'apps':
        return <AppBundles />;
      case 'nerodrop':
        return <NeroDrop />;
      case 'risk':
        return <BehavioralRiskDashboard onSelectNode={(node) => setSelectedNode(node)} />;
      case 'acls':
        return <SettingsACL />;
      case 'audit':
        return <AuditLogs />;
      case 'users':
        return <UserManagement />;
      case 'settings':
        return <MeshSettingsView />;
      case 'nuke':
        return (
          <NeroNukePanel
            nukeArmed={nukeArmed}
            nukeScheduledAt={nukeScheduledAt}
            onArmNuke={handleArmNuke}
            onDisarmNuke={handleDisarmNuke}
            onOpenSecretModal={() => setIsSecretModalOpen(true)}
          />
        );
      default:
        return <Overview onSelectNode={(node) => setSelectedNode(node)} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-dark-canvas text-slate-100 font-sans">
      {/* Persistent Enterprise Cyber Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        nodeCount={18}
        quarantinedCount={1}
        highRiskCount={2}
        nukeArmed={nukeArmed}
        nukeScheduledAt={nukeScheduledAt}
        onNukeClick={() => setActiveTab('nuke')}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top HUD Header */}
        <Header
          onOpenEnrollModal={() => setIsEnrollModalOpen(true)}
          activeTab={activeTab}
        />

        {/* Dynamic Tab Body */}
        <main className="p-6 flex-1 max-w-7xl w-full mx-auto">
          {renderActiveView()}
        </main>
      </div>

      {/* Global Node Actions Slide-Over Drawer */}
      <NodeActions
        node={selectedNode}
        isOpen={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        onNodeUpdated={(updated) => setSelectedNode(updated)}
        onNodeRevoked={() => setSelectedNode(null)}
        onNavigateTab={(tab) => setActiveTab(tab)}
      />

      {/* Cryptographic Profile & QR Code Modal */}
      <CryptoConfigModal
        isOpen={isEnrollModalOpen}
        onClose={() => setIsEnrollModalOpen(false)}
        onNodeEnrolled={(node) => setSelectedNode(node)}
      />

      {/* Steganographic Secret Access Modal (Tier 1b DMS) */}
      <NeroNukeSecretAccessModal
        isOpen={isSecretModalOpen}
        onClose={() => setIsSecretModalOpen(false)}
        onAuthenticated={() => {
          // Secret access successful
        }}
      />
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainConsole />
    </AuthProvider>
  );
}
