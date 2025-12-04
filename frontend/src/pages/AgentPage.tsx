import ColorBends from "../components/ColorBends";
import LaunchAgentForm from "../components/LaunchAgentForm";
function AgentPage() {
  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      {/* Fullscreen background */}
      <div style={{ position: "absolute", inset: 0, zIndex: 0 }}>
        <ColorBends
          colors={["#FFAD00", "#C724B1", "#4D4DFF"]}
          rotation={45}
          speed={0.8}
          scale={1}
          frequency={1.5}
          warpStrength={1.2}
          mouseInfluence={0.8}
          parallax={1}
          noise={0.1}
        />
      </div>
      <div
        className="vertical-center"
        style={{ position: "relative", zIndex: 10 }}
      >
        <LaunchAgentForm />
      </div>
    </div>
  );
}
export default AgentPage;
