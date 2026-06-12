import 'package:flutter/material.dart';

import '../theme/app_theme.dart';
import '../utils/responsive.dart';

class AppScreenShell extends StatelessWidget {
  const AppScreenShell({
    super.key,
    required this.child,
    this.appBar,
    this.padding,
    this.scrollable = false,
  });

  final Widget child;
  final PreferredSizeWidget? appBar;
  final EdgeInsets? padding;
  final bool scrollable;

  @override
  Widget build(BuildContext context) {
    final resolvedPadding =
        padding ?? EdgeInsets.all(AppResponsive.horizontalPadding(context));

    return Scaffold(
      resizeToAvoidBottomInset: true,
      extendBodyBehindAppBar: appBar != null,
      appBar: appBar,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Color(0xFF0B1220),
              Color(0xFF111B2E),
              Color(0xFF0A1628),
            ],
          ),
        ),
        child: SafeArea(
          child: scrollable
              ? _ScrollableBody(padding: resolvedPadding, child: child)
              : Padding(padding: resolvedPadding, child: child),
        ),
      ),
    );
  }
}

class _ScrollableBody extends StatelessWidget {
  const _ScrollableBody({
    required this.padding,
    required this.child,
  });

  final EdgeInsets padding;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          padding: padding,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          child: ConstrainedBox(
            constraints: BoxConstraints(
              minHeight: constraints.maxHeight - padding.vertical,
            ),
            child: child,
          ),
        );
      },
    );
  }
}

class BrandHeader extends StatelessWidget {
  const BrandHeader({
    super.key,
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.accent.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: AppColors.accent.withValues(alpha: 0.35)),
          ),
          child: const Text(
            'IA FACIAL ENTERPRISE',
            style: TextStyle(
              color: AppColors.accent,
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.1,
            ),
          ),
        ),
        const SizedBox(height: 14),
        Text(
          title,
          style: TextStyle(
            color: AppColors.textPrimary,
            fontSize: AppResponsive.titleSize(context),
            fontWeight: FontWeight.w800,
            height: 1.1,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          subtitle,
          style: TextStyle(
            color: AppColors.textMuted,
            fontSize: AppResponsive.bodySize(context),
            height: 1.4,
          ),
        ),
      ],
    );
  }
}
