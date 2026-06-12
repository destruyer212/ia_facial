import 'package:flutter/material.dart';

class AppResponsive {
  static bool isCompact(BuildContext context) =>
      MediaQuery.sizeOf(context).width < 360;

  static bool isShortScreen(BuildContext context) =>
      MediaQuery.sizeOf(context).height < 680;

  static double titleSize(BuildContext context) =>
      isCompact(context) ? 24 : 28;

  static double bodySize(BuildContext context) =>
      isCompact(context) ? 14 : 15;

  static double horizontalPadding(BuildContext context) =>
      isCompact(context) ? 16 : 20;

  static double scanBottomReserved(BuildContext context, {bool showErrorButton = false}) {
    final height = MediaQuery.sizeOf(context).height;
    final base = isShortScreen(context) ? 0.36 : 0.34;
    final extra = showErrorButton ? 0.06 : 0;
    return height * (base + extra);
  }

  static double scanTopReserved(BuildContext context) =>
      MediaQuery.paddingOf(context).top + 64;
}
