class Message {
  final String text;
  final bool isUser;
  final bool isWelcome;

  Message({required this.text, required this.isUser, this.isWelcome = false});
}
