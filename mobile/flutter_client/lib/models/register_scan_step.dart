class RegisterScanStep {
  const RegisterScanStep({
    required this.key,
    required this.label,
    required this.prompt,
    required this.matchesPose,
  });

  final String key;
  final String label;
  final String prompt;
  final bool Function(double headEulerY) matchesPose;
}

const registerScanSteps = [
  RegisterScanStep(
    key: 'front',
    label: 'Frontal',
    prompt: 'Mira al frente',
    matchesPose: _frontPose,
  ),
  RegisterScanStep(
    key: 'left',
    label: 'Giro izquierda',
    prompt: 'Gira lentamente a la izquierda',
    matchesPose: _leftPose,
  ),
  RegisterScanStep(
    key: 'right',
    label: 'Giro derecha',
    prompt: 'Gira lentamente a la derecha',
    matchesPose: _rightPose,
  ),
];

bool _frontPose(double y) => y.abs() <= 22;
bool _leftPose(double y) => y <= -12;
bool _rightPose(double y) => y >= 12;
