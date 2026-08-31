import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode';
import { api } from '../services/api';
import {
  Box,
  Monitor,
  Cloud,
  Image,
  FolderSync,
  Play,
  Square,
  ExternalLink,
  Cpu,
  HardDrive,
  Activity,
  Layers,
  Plus,
  X,
  Lock,
  Sparkles,
  Zap,
  Globe,
  Share2,
  Copy,
  Check,
  QrCode,
  Key,
  Trash2,
  Clock,
  ShieldCheck,
  AlertCircle
} from 'lucide-react';

export default function AppBundles() {
  const [apps, setApps] = useState([]);
  const [isProvisionOpen, setIsProvisionOpen] = useState(false);
  const [ssoModalData, setSsoModalData] = useState(null);

  // Public Share Link Modal State
  const [selectedShareApp, setSelectedShareApp] = useState(null);
  const [isShareModalOpen, setIsShareModalOpen] = useState(false);
  const [shareTab, setShareTab] = useState('generate'); // 'generate' | 'active'
  const [authMode, setAuthMode] = useState('temporary_password');
  const [expiresInHours, setExpiresInHours] = useState(24);
  const [maxUses, setMaxUses] = useState(0);
  const [customPassword, setCustomPassword] = useState('');
  const [isGeneratingShareLink, setIsGeneratingShareLink] = useState(false);
  const [latestShareLink, setLatestShareLink] = useState(null);
  const [activeShareLinks, setActiveShareLinks] = useState([]);
  const [shareQrCodeUrl, setShareQrCodeUrl] = useState('');
  const [copiedShareUrl, setCopiedShareUrl] = useState(false);
  const [copiedSharePass, setCopiedSharePass] = useState(false);
  const [isRevokingLinkId, setIsRevokingLinkId] = useState(null);

  // Form State
  const [appName, setAppName] = useState('');
  const [appType, setAppType] = useState('guacamole');
  const [appTier, setAppTier] = useState('managed_cloud');
  const [cpuCores, setCpuCores] = useState(4.0);
  const [memoryMb, setMemoryMb] = useState(8192);
  const [storageGb, setStorageGb] = useState(250);
  const [scaleToZero, setScaleToZero] = useState(true);

  const loadApps = async () => {
    try {
      const list = await api.apps.list();
      setApps(list);
    } catch (err) {
      console.error('Failed to load app bundles:', err);
    }
  };

  useEffect(() => {
    loadApps();
  }, []);

  const handleAction = async (id, actionType) => {
    await api.apps.action(id, actionType);
    loadApps();
  };

  const handleLaunchSSO = async (id) => {
    const launchData = await api.apps.launch(id);
    setSsoModalData(launchData);
  };

  const handleOpenShareModal = async (app) => {
    setSelectedShareApp(app);
    setIsShareModalOpen(true);
    setShareTab('generate');
    setLatestShareLink(null);
    setShareQrCodeUrl('');
    setCustomPassword('');
    loadShareLinks(app.id);
  };

  const loadShareLinks = async (appId) => {
    try {
      const links = await api.apps.listShareLinks(appId);
      setActiveShareLinks(Array.isArray(links) ? links : []);
    } catch (err) {
      console.error('Failed to load share links:', err);
    }
  };

  const handleGenerateShareLink = async (e) => {
    e.preventDefault();
    if (!selectedShareApp) return;
    setIsGeneratingShareLink(true);
    try {
      const result = await api.apps.createShareLink(selectedShareApp.id, {
        auth_mode: authMode,
        expires_in_hours: expiresInHours,
        max_uses: maxUses,
        temporary_password: customPassword.trim() || undefined
      });
      setLatestShareLink(result);
      if (result && result.public_url) {
        try {
          const qr = await QRCode.toDataURL(result.public_url, {
            errorCorrectionLevel: 'M',
            margin: 2,
            width: 240,
            color: { dark: '#06b6d4', light: '#09090b' }
          });
          setShareQrCodeUrl(qr);
        } catch (err) {
          console.error('QR generation failed:', err);
        }
      }
      loadShareLinks(selectedShareApp.id);
    } catch (err) {
      console.error('Failed to generate share link:', err);
    } finally {
      setIsGeneratingShareLink(false);
    }
  };

  const handleRevokeShareLink = async (linkId) => {
    if (!selectedShareApp) return;
    setIsRevokingLinkId(linkId);
    try {
      await api.apps.revokeShareLink(selectedShareApp.id, linkId);
      loadShareLinks(selectedShareApp.id);
      if (latestShareLink && latestShareLink.id === linkId) {
        setLatestShareLink({ ...latestShareLink, is_revoked: true, status: 'revoked' });
      }
    } catch (err) {
      console.error('Failed to revoke share link:', err);
    } finally {
      setIsRevokingLinkId(null);
    }
  };

  const handleCopyText = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'url') {
      setCopiedShareUrl(true);
      setTimeout(() => setCopiedShareUrl(false), 2000);
    } else {
      setCopiedSharePass(true);
      setTimeout(() => setCopiedSharePass(false), 2000);
    }
  };

  const handleCreateApp = async (e) => {
    e.preventDefault();
    await api.apps.create({
      name: appName,
      type: appType,
      tier: appTier,
      cpu_cores: cpuCores,
      memory_mb: memoryMb,
      storage_gb: storageGb,
      scale_to_zero: scaleToZero
    });
    setIsProvisionOpen(false);
    setAppName('');
    loadApps();
  };

  const getAppIcon = (type) => {
    switch (type) {
      case 'guacamole':
        return <Monitor className="w-6 h-6 text-neon-cyan" />;
      case 'nextcloud':
        return <Cloud className="w-6 h-6 text-neon-indigo" />;
      case 'immich':
        return <Image className="w-6 h-6 text-neon-emerald" />;
      case 'seafile':
        return <FolderSync className="w-6 h-6 text-neon-amber" />;
      default:
        return <Box className="w-6 h-6 text-slate-300" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Sovereign App Bundles & Cloud PC Hub</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-neon-indigo/20 text-neon-indigo border border-neon-indigo/40">
              Containerized E2EE
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Dynamic container provisioning with Single Sign-On (SSO), Clientless Public Share Links, and auto-scale-to-zero lifecycle controls.
          </p>
        </div>

        <button
          onClick={() => setIsProvisionOpen(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold font-mono text-xs hover:brightness-110 transition-all shadow-lg"
        >
          <Plus className="w-4 h-4" />
          <span>Provision Service</span>
        </button>
      </div>

      {/* App Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {apps.map((app) => {
          const isRunning = app.status === 'running';
          return (
            <div
              key={app.id}
              className="p-6 rounded-2xl bg-dark-card border border-dark-border space-y-5 shadow-2xl flex flex-col justify-between hover:border-dark-border/80 transition-all"
            >
              {/* Card Header */}
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3.5">
                    <div className="p-3 rounded-xl bg-dark-canvas border border-dark-border">
                      {getAppIcon(app.type)}
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-slate-100">{app.name}</h2>
                      <div className="text-xs font-mono text-slate-400 mt-0.5">
                        {app.endpoint_url}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] font-mono px-2.5 py-1 rounded-full font-bold flex items-center space-x-1.5 ${
                      isRunning
                        ? 'bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40'
                        : 'bg-dark-canvas text-slate-500 border border-dark-border'
                    }`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-neon-emerald animate-ping' : 'bg-slate-600'}`}></span>
                    <span>{app.status.toUpperCase()}</span>
                  </span>
                </div>

                {/* Resource Gauges */}
                <div className="grid grid-cols-3 gap-3 mt-5 p-3 rounded-xl bg-dark-canvas border border-dark-border text-xs font-mono">
                  <div>
                    <div className="text-[10px] text-slate-500 uppercase flex items-center space-x-1">
                      <Cpu className="w-3 h-3 text-neon-cyan" />
                      <span>CPU Cores</span>
                    </div>
                    <div className="font-bold text-slate-200 mt-0.5">{app.cpu_cores} vCPU</div>
                  </div>

                  <div>
                    <div className="text-[10px] text-slate-500 uppercase flex items-center space-x-1">
                      <Activity className="w-3 h-3 text-neon-indigo" />
                      <span>RAM Memory</span>
                    </div>
                    <div className="font-bold text-slate-200 mt-0.5">{(app.memory_mb / 1024).toFixed(1)} GB</div>
                  </div>

                  <div>
                    <div className="text-[10px] text-slate-500 uppercase flex items-center space-x-1">
                      <HardDrive className="w-3 h-3 text-neon-emerald" />
                      <span>E2EE Storage</span>
                    </div>
                    <div className="font-bold text-slate-200 mt-0.5">{app.storage_gb} GB</div>
                  </div>
                </div>
              </div>

              {/* Card Footer: Lifecycle & Launch Controls */}
              <div className="pt-4 border-t border-dark-border/80 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center space-x-2">
                  {isRunning ? (
                    <button
                      onClick={() => handleAction(app.id, 'stop')}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-dark-canvas border border-neon-rose/40 text-neon-rose text-xs font-mono hover:bg-neon-rose/10 transition-colors"
                    >
                      <Square className="w-3.5 h-3.5" />
                      <span>Stop</span>
                    </button>
                  ) : (
                    <button
                      onClick={() => handleAction(app.id, 'start')}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-dark-canvas border border-neon-emerald/40 text-neon-emerald text-xs font-mono hover:bg-neon-emerald/10 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Start</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleAction(app.id, 'scale_to_zero')}
                    className={`text-[11px] font-mono px-2.5 py-1.5 rounded border transition-all ${
                      app.scale_to_zero
                        ? 'bg-neon-cyan/20 text-neon-cyan border-neon-cyan/40'
                        : 'bg-dark-canvas text-slate-500 border-dark-border'
                    }`}
                    title="Scale container to zero when idle for 30 mins"
                  >
                    Auto-Scale: {app.scale_to_zero ? 'ON' : 'OFF'}
                  </button>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleOpenShareModal(app)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-dark-canvas border border-neon-cyan/40 text-neon-cyan hover:bg-neon-cyan/15 font-mono text-xs font-bold transition-all shadow-sm"
                    title="Generate Public Share Link (Clientless RDP)"
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>Public Share</span>
                  </button>

                  <button
                    onClick={() => handleLaunchSSO(app.id)}
                    disabled={!isRunning}
                    className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold font-mono text-xs hover:brightness-110 disabled:opacity-40 transition-all shadow-md"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Launch SSO</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Launch SSO Modal Simulator */}
      {ssoModalData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-dark-border pb-3">
              <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono">
                <Sparkles className="w-4 h-4 text-neon-cyan" />
                <span>NeroNet SSO Authenticated Launch</span>
              </div>
              <button onClick={() => setSsoModalData(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 font-mono">
              Generating ephemeral OIDC/SAML Single Sign-On ticket for <strong>{ssoModalData.app_name}</strong>...
            </p>

            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border font-mono text-xs text-neon-cyan break-all">
              {ssoModalData.launch_url}
            </div>

            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border font-mono text-xs text-slate-400 space-y-1">
              <div>SSO Token: <span className="text-slate-200">{ssoModalData.sso_token}</span></div>
              <div>Security Protocol: WireGuard Overlay / Zero-Knowledge Handshake</div>
            </div>

            <div className="flex justify-end space-x-3 pt-2">
              <button
                onClick={() => setSsoModalData(null)}
                className="px-4 py-2 rounded-lg bg-dark-border text-slate-300 text-xs font-mono"
              >
                Dismiss
              </button>
              <a
                href={ssoModalData.launch_url}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold text-xs font-mono hover:brightness-110"
              >
                Open Service WebUI &rarr;
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Provision App Bundle Modal */}
      {isProvisionOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-dark-border flex items-center justify-between bg-dark-canvas">
              <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono">
                <Box className="w-4 h-4 text-neon-cyan" />
                <span>Provision New App Bundle</span>
              </div>
              <button onClick={() => setIsProvisionOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateApp} className="p-6 space-y-4 text-xs font-mono">
              <div>
                <label className="block text-slate-400 mb-1">Service Instance Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. My Guacamole Cloud PC"
                  value={appName}
                  onChange={(e) => setAppName(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Application Type</label>
                  <select
                    value={appType}
                    onChange={(e) => setAppType(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="guacamole">Guacamole Cloud PC</option>
                    <option value="nextcloud">Nextcloud Files</option>
                    <option value="immich">Immich Photo Vault</option>
                    <option value="seafile">Seafile Sync</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Deployment Tier</label>
                  <select
                    value={appTier}
                    onChange={(e) => setAppTier(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="managed_cloud">Managed Cloud</option>
                    <option value="self_hosted_byos">Self-Hosted BYOS</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">vCPU Cores</label>
                  <input
                    type="number"
                    value={cpuCores}
                    onChange={(e) => setCpuCores(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">RAM (MB)</label>
                  <input
                    type="number"
                    value={memoryMb}
                    onChange={(e) => setMemoryMb(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Storage (GB)</label>
                  <input
                    type="number"
                    value={storageGb}
                    onChange={(e) => setStorageGb(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsProvisionOpen(false)}
                  className="px-4 py-2 rounded-lg bg-dark-border text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold hover:brightness-110"
                >
                  Deploy Bundle
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Public Share Link Modal (Clientless RDP Gateway) */}
      {isShareModalOpen && selectedShareApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="p-5 border-b border-dark-border flex items-center justify-between bg-dark-canvas/50">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 rounded-xl bg-neon-cyan/10 border border-neon-cyan/30 flex items-center justify-center glow-cyan">
                  <Globe className="w-5 h-5 text-neon-cyan" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
                    <span>Clientless Public Share Links</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40">
                      {selectedShareApp.name}
                    </span>
                  </h2>
                  <p className="text-xs text-slate-400">
                    Secure WAN internet access via Zero-Trust SSO / temporary password without requiring VPN client installation.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsShareModalOpen(false)}
                className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-dark-card-hover transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Sub-nav Tabs */}
            <div className="px-6 pt-3 border-b border-dark-border flex items-center space-x-4 bg-dark-canvas/30 text-xs font-mono">
              <button
                onClick={() => setShareTab('generate')}
                className={`pb-3 border-b-2 font-bold transition-all flex items-center space-x-1.5 ${
                  shareTab === 'generate'
                    ? 'border-neon-cyan text-neon-cyan'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Create Share Link</span>
              </button>
              <button
                onClick={() => setShareTab('active')}
                className={`pb-3 border-b-2 font-bold transition-all flex items-center space-x-1.5 ${
                  shareTab === 'active'
                    ? 'border-neon-cyan text-neon-cyan'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Active Links ({activeShareLinks.filter(l => !l.is_revoked && !l.is_expired).length})</span>
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-xs font-mono">
              {shareTab === 'generate' && (
                <div className="space-y-5">
                  <form onSubmit={handleGenerateShareLink} className="p-4 rounded-xl bg-dark-canvas/80 border border-dark-border space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <label className="block text-slate-400 mb-1">Authentication Mode</label>
                        <select
                          value={authMode}
                          onChange={(e) => setAuthMode(e.target.value)}
                          className="w-full px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan text-xs"
                        >
                          <option value="temporary_password">Temporary Password</option>
                          <option value="sso_gateway">SSO Gateway Auth</option>
                          <option value="passkey">WebAuthn Passkey</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-slate-400 mb-1">Link Expiration</label>
                        <select
                          value={expiresInHours}
                          onChange={(e) => setExpiresInHours(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan text-xs"
                        >
                          <option value={1}>1 Hour</option>
                          <option value={24}>24 Hours (1 Day)</option>
                          <option value={168}>7 Days (1 Week)</option>
                          <option value={720}>30 Days (1 Month)</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-slate-400 mb-1">Usage Counter Limit</label>
                        <select
                          value={maxUses}
                          onChange={(e) => setMaxUses(Number(e.target.value))}
                          className="w-full px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan text-xs"
                        >
                          <option value={0}>Unlimited Uses</option>
                          <option value={1}>Single-Use (1 Time)</option>
                          <option value={5}>5 Uses</option>
                          <option value={10}>10 Uses</option>
                        </select>
                      </div>
                    </div>

                    {authMode === 'temporary_password' && (
                      <div>
                        <label className="block text-slate-400 mb-1">
                          Custom Temporary Password <span className="text-slate-600">(Optional — auto-generated if blank)</span>
                        </label>
                        <input
                          type="text"
                          placeholder="e.g. SVRN-GUEST-SECURE"
                          value={customPassword}
                          onChange={(e) => setCustomPassword(e.target.value)}
                          className="w-full px-3 py-2 bg-dark-card border border-dark-border rounded-lg text-slate-100 placeholder-slate-600 focus:outline-none focus:border-neon-cyan font-mono text-xs"
                        />
                      </div>
                    )}

                    <div className="pt-2 flex justify-end">
                      <button
                        type="submit"
                        disabled={isGeneratingShareLink}
                        className="px-5 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold text-xs hover:brightness-110 disabled:opacity-50 transition-all flex items-center space-x-2 shadow-lg"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{isGeneratingShareLink ? 'Generating...' : 'Generate Public Link'}</span>
                      </button>
                    </div>
                  </form>

                  {/* Generated Link Display */}
                  {latestShareLink && (
                    <div className="p-5 rounded-xl bg-dark-canvas border border-neon-cyan/40 space-y-4 animate-in fade-in duration-200 glow-cyan">
                      <div className="flex items-center justify-between border-b border-dark-border pb-3">
                        <div className="flex items-center space-x-2 text-neon-cyan font-bold">
                          <ShieldCheck className="w-4 h-4" />
                          <span>Public Link Active & Ready</span>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/30">
                          Expires in {expiresInHours}h
                        </span>
                      </div>

                      {/* Public URL Box */}
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase mb-1">Public WAN Gateway URL</div>
                        <div className="flex items-center space-x-2 bg-dark-card p-2 rounded-lg border border-dark-border">
                          <input
                            readOnly
                            value={latestShareLink.public_url}
                            className="w-full bg-transparent text-neon-cyan text-xs font-mono focus:outline-none"
                          />
                          <button
                            type="button"
                            onClick={() => handleCopyText(latestShareLink.public_url, 'url')}
                            className="px-3 py-1 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40 rounded hover:bg-neon-cyan/30 text-xs font-mono font-bold flex items-center space-x-1 transition-all"
                          >
                            {copiedShareUrl ? <Check className="w-3.5 h-3.5 text-neon-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                            <span>{copiedShareUrl ? 'Copied' : 'Copy'}</span>
                          </button>
                        </div>
                      </div>

                      {/* Temporary Password Box */}
                      {latestShareLink.temporary_password && (
                        <div>
                          <div className="text-[10px] text-slate-400 uppercase mb-1">Temporary Access Password</div>
                          <div className="flex items-center space-x-2 bg-dark-card p-2 rounded-lg border border-dark-border">
                            <input
                              readOnly
                              value={latestShareLink.temporary_password}
                              className="w-full bg-transparent text-neon-emerald font-bold text-xs font-mono focus:outline-none tracking-wider"
                            />
                            <button
                              type="button"
                              onClick={() => handleCopyText(latestShareLink.temporary_password, 'pass')}
                              className="px-3 py-1 bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40 rounded hover:bg-neon-emerald/30 text-xs font-mono font-bold flex items-center space-x-1 transition-all"
                            >
                              {copiedSharePass ? <Check className="w-3.5 h-3.5 text-neon-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                              <span>{copiedSharePass ? 'Copied' : 'Copy'}</span>
                            </button>
                          </div>
                        </div>
                      )}

                      {/* QR Code Preview */}
                      {shareQrCodeUrl && (
                        <div className="pt-2 flex flex-col sm:flex-row items-center sm:space-x-4 space-y-3 sm:space-y-0 p-3 bg-dark-card rounded-xl border border-dark-border/80">
                          <img
                            src={shareQrCodeUrl}
                            alt="Public Share QR Code"
                            className="w-28 h-28 rounded-lg border border-neon-cyan/30 bg-black p-1"
                          />
                          <div className="space-y-1 text-center sm:text-left">
                            <div className="font-bold text-slate-200 text-xs">Instant Clientless QR Access</div>
                            <p className="text-[11px] text-slate-400">
                              Scan with any smartphone, tablet, or external laptop to access Guacamole RDP without installing software.
                            </p>
                            <div className="text-[10px] text-slate-500 font-mono pt-1">
                              Protocol: Guacamole WebSockets &bull; E2EE TLS 1.3 &bull; Max Uses: {latestShareLink.max_uses || 'Unlimited'}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {shareTab === 'active' && (
                <div className="space-y-3">
                  {activeShareLinks.length === 0 ? (
                    <div className="py-10 text-center text-slate-500 border border-dashed border-dark-border rounded-xl">
                      No public share links generated yet for this application.
                    </div>
                  ) : (
                    activeShareLinks.map((link) => {
                      const isRevoked = link.is_revoked || link.status === 'revoked';
                      const isExpired = link.is_expired || link.status === 'expired' || new Date(link.expires_at).getTime() < Date.now();
                      return (
                        <div
                          key={link.id}
                          className={`p-4 rounded-xl border space-y-2.5 transition-all ${
                            isRevoked
                              ? 'bg-neon-rose/5 border-neon-rose/30 opacity-70'
                              : isExpired
                              ? 'bg-dark-card/50 border-dark-border opacity-70'
                              : 'bg-dark-canvas border-dark-border hover:border-neon-cyan/30'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                                  isRevoked
                                    ? 'bg-neon-rose/20 text-neon-rose border border-neon-rose/40'
                                    : isExpired
                                    ? 'bg-neon-amber/20 text-neon-amber border border-neon-amber/40'
                                    : 'bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40'
                                }`}
                              >
                                {isRevoked ? 'REVOKED' : isExpired ? 'EXPIRED' : 'ACTIVE'}
                              </span>
                              <span className="text-slate-300 font-bold text-xs">{link.auth_mode}</span>
                            </div>

                            {!isRevoked && !isExpired && (
                              <button
                                onClick={() => handleRevokeShareLink(link.id)}
                                disabled={isRevokingLinkId === link.id}
                                className="flex items-center space-x-1 px-2.5 py-1 rounded bg-dark-card border border-neon-rose/40 text-neon-rose hover:bg-neon-rose/15 text-[11px] font-mono transition-colors disabled:opacity-50"
                              >
                                <Trash2 className="w-3 h-3" />
                                <span>{isRevokingLinkId === link.id ? 'Revoking...' : 'Revoke Link'}</span>
                              </button>
                            )}
                          </div>

                          <div className="text-[11px] text-slate-400 font-mono break-all flex items-center justify-between">
                            <span className="truncate mr-2">{link.public_url}</span>
                            <button
                              onClick={() => handleCopyText(link.public_url, 'url')}
                              className="p-1 text-slate-400 hover:text-white shrink-0"
                            >
                              <Copy className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500 pt-1 border-t border-dark-border/60">
                            <div>Expires: {new Date(link.expires_at).toLocaleString()}</div>
                            <div>Uses: {link.use_count || 0} / {link.max_uses > 0 ? link.max_uses : '∞'}</div>
                            {link.temporary_password && (
                              <div className="text-neon-emerald font-bold">Pass: {link.temporary_password}</div>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-dark-border bg-dark-canvas/50 flex justify-end">
              <button
                onClick={() => setIsShareModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-dark-border text-slate-300 hover:text-white text-xs font-mono transition-colors"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
