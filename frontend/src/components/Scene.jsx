import React from "react";
import { StructureFlowCollection } from "@designcodeio/threeui";
import "@designcodeio/threeui/style.css";

export function Scene() {
  return (
    <div className="shader-frame">
      <StructureFlowCollection
        variant="orbital-sphere"
        speed={1.54}
        particleSize={0.040}
        particleOpacity={1.00}
        orbitOpacity={0.55}
        hue={-60}
        scale={0.93}
        haloOpacity={0.75}
      />
    </div>
  );
}

export default Scene;
