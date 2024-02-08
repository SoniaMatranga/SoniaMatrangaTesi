//file da cancellare

package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"net"
)

func main() {
	// Connessione al server Python
	conn, err := net.Dial("tcp", "localhost:8765")
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()
	valueToSend := "172.19.0.3"
	fmt.Fprintf(conn, "getSuggestion %s\n", valueToSend)

	// Invia una richiesta
	fmt.Fprintln(conn, "getSuggestion")

	// Leggi la risposta
	response, err := bufio.NewReader(conn).ReadString('\n')
	if err != nil {
		if err == io.EOF {
			fmt.Println("Connessione chiusa dal server.")
		} else {
			log.Fatal(err)
		}
	} else {
		// Stampa la risposta
		fmt.Printf("Got suggestion: %s\n", response)
	}

	// Stampa la risposta
	fmt.Printf("Got suggestion: %s\n", response)
}
