import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";


export class ActuatorViewer {
  constructor(container) {
    if (!(container instanceof HTMLElement)) {
      throw new TypeError(
        "ActuatorViewer requires a valid HTML container",
      );
    }

    this.container = container;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf1f3f5);

    this.camera = new THREE.PerspectiveCamera(
      45,
      1,
      0.01,
      100,
    );

    this.camera.position.set(2.8, 2.2, 2.4);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
    });

    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.setPixelRatio(
      Math.min(window.devicePixelRatio, 2),
    );

    this.renderer.domElement.setAttribute(
      "aria-label",
      "3D actuator visualization",
    );

    this.container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(
      this.camera,
      this.renderer.domElement,
    );

    this.controls.target.set(0, 0, 0.45);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;

    this.controls.minDistance = 1.5;
    this.controls.maxDistance = 7.0;

    this.rotatingJoint = new THREE.Group();

    this._createLights();
    this._createEnvironment();
    this._createActuator();

    this.resizeObserver = new ResizeObserver(() => {
      this.resize();
    });

    this.resizeObserver.observe(this.container);

    this.running = false;
    this.animationFrame = null;

    this.resize();
  }

  _createLights() {
    const ambientLight = new THREE.HemisphereLight(
      0xffffff,
      0x444444,
      2.0,
    );

    this.scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(
      0xffffff,
      3.0,
    );

    mainLight.position.set(3, 4, 5);
    this.scene.add(mainLight);

    const fillLight = new THREE.DirectionalLight(
      0xffffff,
      1.0,
    );

    fillLight.position.set(-3, -2, 2);
    this.scene.add(fillLight);
  }

  _createEnvironment() {
    const grid = new THREE.GridHelper(
      6,
      30,
      0x6c757d,
      0xc4c9ce,
    );

    // Three.js GridHelper is created in the XZ plane.
    this.scene.add(grid);

    const axes = new THREE.AxesHelper(0.6);
    axes.position.set(-1.1, -1.1, 0.01);
    this.scene.add(axes);
  }

  _createActuator() {
    const bodyMaterial = new THREE.MeshStandardMaterial({
      color: 0x4d5964,
      metalness: 0.35,
      roughness: 0.55,
    });

    const flangeMaterial = new THREE.MeshStandardMaterial({
      color: 0x89939d,
      metalness: 0.65,
      roughness: 0.3,
    });

    const movingMaterial = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      metalness: 0.25,
      roughness: 0.45,
    });

    const darkMaterial = new THREE.MeshStandardMaterial({
      color: 0x252b31,
      metalness: 0.45,
      roughness: 0.4,
    });

    /*
     * The model uses Z as the joint axis, matching a typical ROS
     * revolute joint whose axis is [0, 0, 1].
     */

    const bodyGeometry = new THREE.CylinderGeometry(
      0.55,
      0.55,
      0.65,
      48,
    );

    const body = new THREE.Mesh(
      bodyGeometry,
      bodyMaterial,
    );

    // CylinderGeometry is aligned with Y by default.
    body.rotation.x = Math.PI / 2;
    body.position.z = 0.35;

    this.scene.add(body);

    const rearGeometry = new THREE.CylinderGeometry(
      0.42,
      0.42,
      0.12,
      48,
    );

    const rear = new THREE.Mesh(
      rearGeometry,
      darkMaterial,
    );

    rear.rotation.x = Math.PI / 2;
    rear.position.z = 0.02;

    this.scene.add(rear);

    const flangeGeometry = new THREE.CylinderGeometry(
      0.68,
      0.68,
      0.12,
      48,
    );

    const flange = new THREE.Mesh(
      flangeGeometry,
      flangeMaterial,
    );

    flange.rotation.x = Math.PI / 2;
    flange.position.z = 0.72;

    this.scene.add(flange);

    /*
     * Everything attached to rotatingJoint follows the measured
     * actuator position.
     */
    this.rotatingJoint.position.z = 0.81;
    this.scene.add(this.rotatingJoint);

    const shaftGeometry = new THREE.CylinderGeometry(
      0.16,
      0.16,
      0.34,
      32,
    );

    const shaft = new THREE.Mesh(
      shaftGeometry,
      darkMaterial,
    );

    shaft.rotation.x = Math.PI / 2;
    shaft.position.z = 0.17;

    this.rotatingJoint.add(shaft);

    const armGeometry = new THREE.BoxGeometry(
      1.15,
      0.16,
      0.12,
    );

    const arm = new THREE.Mesh(
      armGeometry,
      movingMaterial,
    );

    /*
     * Offset by half its length so the arm rotates around one end.
     */
    arm.position.set(0.575, 0, 0.36);

    this.rotatingJoint.add(arm);

    const arrowLength = 0.40;
    const arrowRadius = 0.18;

    const endGeometry = new THREE.ConeGeometry(
      arrowRadius,
      arrowLength,
      32,
    );

    const end = new THREE.Mesh(
      endGeometry,
      movingMaterial,
    );

    /*
    * ConeGeometry is aligned with the Y axis and points toward +Y.
    * Rotate it so the tip points toward +X.
    */
    end.rotation.z = -Math.PI / 2;

    /*
    * Cone position refers to its center. The arm ends at x = 1.15,
    * so move the cone by half its length.
    */
    end.position.set(
      1.15 + arrowLength / 2,
      0,
      0.36,
    );

    this.rotatingJoint.add(end);
  }

  setPosition(position) {
    if (!Number.isFinite(position)) {
      return;
    }

    /*
     * ROS joint positions are expressed in radians, as is
     * THREE.Object3D.rotation.
     */
    this.rotatingJoint.rotation.z = position;
  }

  resize() {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;

    if (width <= 0 || height <= 0) {
      return;
    }

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height, false);
  }

  start() {
    if (this.running) {
      return;
    }

    this.running = true;

    const renderFrame = () => {
      if (!this.running) {
        return;
      }

      this.controls.update();
      this.renderer.render(this.scene, this.camera);

      this.animationFrame = requestAnimationFrame(renderFrame);
    };

    renderFrame();
  }

  stop() {
    this.running = false;

    if (this.animationFrame !== null) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
  }

  resetCamera() {
    this.camera.position.set(2.8, 2.2, 2.4);
    this.controls.target.set(0, 0, 0.45);
    this.controls.update();
  }

  dispose() {
    this.stop();
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.renderer.dispose();

    this.container.replaceChildren();
  }
}