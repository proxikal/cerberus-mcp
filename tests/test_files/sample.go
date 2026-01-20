// Sample Go file for parser testing.
package main

import "fmt"

// Widget is a sample struct.
type Widget struct {
	Name  string
	Value int
}

func Greet(name string) string {
	return fmt.Sprintf("Hello, %s!", name)
}

func add(a, b int) int {
	return a + b
}
