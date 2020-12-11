class Example {
   static void main(String[] args) {
      String a = "1.0.1";
      String[] str;
      str = a.split('\\.');
      
      for( String values : str )
      println(values);
   } 
}
